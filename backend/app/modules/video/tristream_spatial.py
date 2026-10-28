"""
Module 3 — Task 2: Landmark-Anchored Spatial Forensics (Spatial Stream).

Architecture references:
  - video_forensics_tech_spec.md Task 2 (Landmark-Anchored Explainability)
  - architecture.md Module 3 §3 Spatial stream

Pipeline:
  1. Load a pretrained ViT (SiglipForImageClassification backbone, or ViT-Base
     as a drop-in if the Siglip checkpoint isn't cached yet) with
     output_attentions=True.
  2. Run the padded face crop through the model.
  3. Compute Attention Rollout across all transformer layers:
       rollout[0] = identity
       for each layer: rollout = rollout @ (0.5 * attn + 0.5 * I)
     This gives a spatial attention map over ViT patch tokens.
  4. Reshape from token space → image space (HxW heatmap).
  5. Intersect with MediaPipe landmark positions to produce one human-readable
     localization string (e.g. "lower chin boundary") — directly satisfying
     Deliverable 5 without any post-hoc LLM guess.
  6. Save attention overlay to /tmp/ as the saliency_heatmap_path.

Spatial anomaly score:
  Deepfake compositing artefacts cluster at facial BOUNDARIES (jaw seam, neck
  blend, ear edge), not at the central forehead/cheek region. The spatial_anomaly_score
  = (boundary attention mean) / (centre attention mean) — a boundary-biased model
  strongly suggests a face-swap seam.

Model lazy-loading:
  The model is downloaded once and cached in module-level variables. Docker image
  build does NOT pull weights; they are fetched on first run() call and cached by
  the HuggingFace transformers library in ~/.cache/huggingface/.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy-loaded model singleton
# ---------------------------------------------------------------------------

_MODEL = None
_PROCESSOR = None

# Primary checkpoint: SiglipVisionModel (attention-accessible ViT backbone).
# Falls back to standard ViT-Base if not available.
_PRIMARY_CKPT = "google/siglip-base-patch16-224"
_FALLBACK_CKPT = "google/vit-base-patch16-224"
_PATCH_SIZE = 16
_INPUT_SIZE = 224   # model's expected input resolution


def _load_model():
    """Lazy-load ViT model + processor. Called once on first use."""
    global _MODEL, _PROCESSOR
    if _MODEL is not None:
        return

    try:
        from transformers import AutoImageProcessor, AutoModel
        logger.info("Spatial: loading model %s ...", _PRIMARY_CKPT)
        _PROCESSOR = AutoImageProcessor.from_pretrained(_PRIMARY_CKPT)
        _MODEL = AutoModel.from_pretrained(
            _PRIMARY_CKPT, output_attentions=True, add_pooling_layer=False
        )
        _MODEL.eval()
        logger.info("Spatial: model loaded (%s).", _PRIMARY_CKPT)
    except Exception as primary_exc:
        logger.warning(
            "Spatial: primary checkpoint failed (%s), trying fallback %s.",
            primary_exc, _FALLBACK_CKPT,
        )
        try:
            from transformers import AutoImageProcessor, AutoModel
            _PROCESSOR = AutoImageProcessor.from_pretrained(_FALLBACK_CKPT)
            _MODEL = AutoModel.from_pretrained(
                _FALLBACK_CKPT, output_attentions=True, add_pooling_layer=False
            )
            _MODEL.eval()
            logger.info("Spatial: fallback model loaded (%s).", _FALLBACK_CKPT)
        except Exception as fallback_exc:
            logger.error("Spatial: both checkpoints failed: %s", fallback_exc)
            _MODEL = None
            _PROCESSOR = None


# ---------------------------------------------------------------------------
# MediaPipe landmark → human-readable label map
# ---------------------------------------------------------------------------

_LANDMARK_LABELS: dict[int, str] = {
    # Chin / jaw
    152: "lower chin boundary",
    172: "lower jaw line",
    136: "left jaw boundary",
    365: "right jaw boundary",
    # Neck / chin seam
    175: "chin-neck junction",
    # Ear region
    234: "left ear boundary",
    454: "right ear boundary",
    # Nose bridge
    6: "nose bridge",
    # Eye corners
    33: "left eye outer corner",
    263: "right eye outer corner",
    # Forehead
    10: "upper forehead",
    # Cheeks
    116: "left cheekbone",
    345: "right cheekbone",
}

_GRID_H = _INPUT_SIZE // _PATCH_SIZE   # 14 for 224/16
_GRID_W = _INPUT_SIZE // _PATCH_SIZE


# ---------------------------------------------------------------------------
# Attention rollout
# ---------------------------------------------------------------------------

def _attention_rollout(attentions: list) -> np.ndarray:
    """
    Compute attention rollout across all transformer layers.
    attentions: list of (1, num_heads, num_tokens, num_tokens) tensors.
    Returns a (num_patches,) array over spatial tokens (excluding CLS).
    """
    import torch

    result = torch.eye(attentions[0].shape[-1])
    for attn in attentions:
        # Average across heads
        attn_avg = attn.squeeze(0).mean(dim=0)  # (tokens, tokens)
        # Add residual: 0.5 * A + 0.5 * I
        attn_aug = 0.5 * attn_avg + 0.5 * torch.eye(attn_avg.shape[0])
        # Normalise rows
        attn_aug /= attn_aug.sum(dim=-1, keepdim=True).clamp(min=1e-8)
        result = attn_aug @ result

    # CLS token (index 0) attending to image patches (indices 1:)
    cls_attn = result[0, 1:].detach().numpy()   # (num_patches,)
    cls_attn = cls_attn / (cls_attn.max() + 1e-8)
    return cls_attn.astype(np.float32)


def _rollout_to_heatmap(rollout: np.ndarray, target_h: int, target_w: int) -> np.ndarray:
    """Reshape rollout to (H, W) and upsample to target resolution."""
    grid = rollout.reshape(_GRID_H, _GRID_W)
    hm = cv2.resize(grid, (target_w, target_h), interpolation=cv2.INTER_LINEAR)
    return hm


def _boundary_vs_centre_score(hm: np.ndarray) -> float:
    """
    Anomaly score = mean attention in the outer 20% boundary ring
                  / mean attention in the inner 60% centre.
    >1 means the model focuses on the facial boundary → seam evidence.
    Clamped to [0, 1].
    """
    h, w = hm.shape
    ph = int(h * 0.20)
    pw = int(w * 0.20)

    boundary_mask = np.ones_like(hm, dtype=bool)
    boundary_mask[ph:h - ph, pw:w - pw] = False

    centre_mask = ~boundary_mask
    boundary_mean = float(hm[boundary_mask].mean()) + 1e-8
    centre_mean = float(hm[centre_mask].mean()) + 1e-8

    ratio = boundary_mean / centre_mean
    # Scale: ratio ~1 → neutral (~0.5). Deepfakes push it toward 2+.
    score = float(np.clip((ratio - 0.7) / 1.6, 0.0, 1.0))
    return score


def _nearest_landmark_label(
    hm: np.ndarray,
    landmarks,
    img_h: int,
    img_w: int,
) -> str:
    """Map peak heatmap location to the closest MediaPipe landmark label."""
    flat_idx = int(np.argmax(hm))
    peak_y = int(flat_idx / hm.shape[1])
    peak_x = int(flat_idx % hm.shape[1])

    # Normalise peak to [0,1] space
    py = peak_y / hm.shape[0]
    px = peak_x / hm.shape[1]

    best_label = "facial boundary"
    best_dist = float("inf")
    for lm_idx, label in _LANDMARK_LABELS.items():
        if lm_idx >= len(landmarks):
            continue
        lm = landmarks[lm_idx]
        dist = (lm.x - px) ** 2 + (lm.y - py) ** 2
        if dist < best_dist:
            best_dist = dist
            best_label = label

    return best_label


def _save_heatmap_overlay(
    face_crop_path: str,
    hm: np.ndarray,
    output_dir: str = "/tmp",
) -> str:
    """Blend heatmap onto face crop and save as JPEG. Returns path."""
    img = cv2.imread(face_crop_path)
    if img is None:
        return ""

    hm_u8 = np.uint8(255 * hm)
    coloured = cv2.applyColorMap(hm_u8, cv2.COLORMAP_JET)
    coloured = cv2.resize(coloured, (img.shape[1], img.shape[0]))
    overlay = cv2.addWeighted(img, 0.55, coloured, 0.45, 0)

    basename = Path(face_crop_path).stem
    out_path = os.path.join(output_dir, f"saliency_{basename}.jpg")
    cv2.imwrite(out_path, overlay)
    return out_path


# ---------------------------------------------------------------------------
# Data class + public API
# ---------------------------------------------------------------------------

@dataclass
class SpatialResult:
    spatial_anomaly_score: Optional[float]
    spatial_localization: Optional[str]
    stream_verdict: str
    heatmap_path: Optional[str]


def analyze_spatial(
    face_crop_path: str,
    landmarks=None,          # MediaPipe landmark list for this crop (optional)
    img_h: int = _INPUT_SIZE,
    img_w: int = _INPUT_SIZE,
) -> SpatialResult:
    """
    Run ViT attention rollout on one face crop.
    Returns SpatialResult with anomaly score, localization text, and heatmap path.
    """
    _load_model()
    if _MODEL is None or _PROCESSOR is None:
        logger.warning("Spatial: model unavailable — returning not_assessed.")
        return SpatialResult(None, None, "not_assessed", None)

    import torch
    from PIL import Image as PILImage

    img_bgr = cv2.imread(face_crop_path)
    if img_bgr is None:
        return SpatialResult(None, None, "not_assessed", None)

    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    pil_img = PILImage.fromarray(img_rgb)

    try:
        inputs = _PROCESSOR(images=pil_img, return_tensors="pt")
        with torch.no_grad():
            outputs = _MODEL(**inputs, output_attentions=True)

        attentions = outputs.attentions   # tuple of (1, heads, tokens, tokens)
    except Exception as exc:
        logger.warning("Spatial: forward pass failed: %s", exc)
        return SpatialResult(None, None, "not_assessed", None)

    rollout = _attention_rollout(list(attentions))
    hm = _rollout_to_heatmap(rollout, img_h, img_w)

    anomaly_score = _boundary_vs_centre_score(hm)

    localization = None
    if landmarks is not None:
        localization = _nearest_landmark_label(hm, landmarks, img_h, img_w)
    else:
        # Fallback: describe peak heatmap quadrant in plain text
        ph, pw = int(np.argmax(hm) / hm.shape[1]), int(np.argmax(hm) % hm.shape[1])
        vert = "upper" if ph < hm.shape[0] // 2 else "lower"
        horiz = "left" if pw < hm.shape[1] // 2 else "right"
        localization = f"{vert}-{horiz} facial region"

    heatmap_path = _save_heatmap_overlay(face_crop_path, hm)

    if anomaly_score >= 0.65:
        verdict = "signal_detected"
    elif anomaly_score <= 0.30:
        verdict = "no_strong_signal_detected"
    else:
        verdict = "inconclusive"

    logger.info(
        "Spatial: score=%.3f localization='%s' verdict=%s",
        anomaly_score, localization, verdict,
    )

    return SpatialResult(
        spatial_anomaly_score=round(anomaly_score, 4),
        spatial_localization=localization,
        stream_verdict=verdict,
        heatmap_path=heatmap_path if heatmap_path else None,
    )


def aggregate_spatial(results: list[SpatialResult]) -> SpatialResult:
    """Aggregate spatial results across crops using peak anomaly score."""
    valid = [r for r in results if r.stream_verdict != "not_assessed" and r.spatial_anomaly_score is not None]
    if not valid:
        return SpatialResult(None, None, "not_assessed", None)

    peak = max(valid, key=lambda r: r.spatial_anomaly_score or 0.0)
    return peak
