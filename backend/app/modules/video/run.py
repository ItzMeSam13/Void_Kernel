"""
Module 3 — Video Intelligence: public entrypoint (Phase 1 + 2 + 3).

Architecture rule (§6):
  - Single public surface: run(input: VideoInput) -> VideoFindings
  - Zero knowledge of LangGraph / ARQ / FastAPI.
  - Callable standalone:
      python -c "
      from pathlib import Path
      from app.modules.video.run import run
      from app.modules.video.contracts import VideoInput
      result = run(VideoInput(video_path=Path('my_video.mp4')))
      print(result.model_dump_json(indent=2))
      "

Phase coverage:
  Phase 1: snippet extraction + MediaPipe FaceMesh (extraction.py)
  Phase 2: spectral DCT split, rPPG, per-frame Module 2 stub calls
  Phase 3: spatial ViT attention rollout, weighted-peak fusion → full contract

Cross-module stubs (stubs.py):
  analyze_image_fn  → Person 3's analyze_image() — swap when Module 2 lands
  reuse_lookup_fn   → Person 1's Module 5 lookup — swap when Module 5 lands
"""

from __future__ import annotations

import logging
from pathlib import Path

import cv2

from app.modules.video.contracts import (
    Verdict,
    VideoFindings,
    VideoInput,
)
from app.modules.video.extraction import extract_snippets
from app.modules.video.fusion import fuse
from app.modules.video.stubs import analyze_image_fn, reuse_lookup_fn
from app.modules.video.tristream_rppg import RppgResult, analyze_rppg
from app.modules.video.tristream_spatial import SpatialResult, aggregate_spatial, analyze_spatial
from app.modules.video.tristream_spectral import SpectralResult, aggregate_spectral, analyze_spectral

logger = logging.getLogger(__name__)

_NOT_ASSESSED_SPECTRAL = SpectralResult(0.0, 0.0, False, "not_assessed")
_NOT_ASSESSED_RPPG = RppgResult(None, None, "not_assessed")
_NOT_ASSESSED_SPATIAL = SpatialResult(None, None, "not_assessed", None)


def _get_fps(video_path: Path) -> float:
    """Read FPS from the video file. Falls back to 30.0 if unreadable."""
    cap = cv2.VideoCapture(str(video_path))
    fps = cap.get(cv2.CAP_PROP_FPS)
    cap.release()
    return fps if fps and fps > 0 else 30.0


def run(input: VideoInput) -> VideoFindings:
    """
    Full tri-stream deepfake analysis pipeline.

    Phase 1: dense snippet extraction + MediaPipe face alignment.
    Phase 2: spectral DCT split, rPPG biometric, per-frame Module 2 stub calls.
    Phase 3: spatial ViT attention rollout, weighted-peak stream fusion.

    Parameters
    ----------
    input : VideoInput
        .video_path: path to the video file.
        .claim_text: optional claim text (forwarded to per-frame analyze_image calls).

    Returns
    -------
    VideoFindings
        Fully-typed output. If a stream is unavailable (model load failure, no
        face detected), its scores are None and its verdict is NOT_ASSESSED —
        partial results are still returned rather than raising (Guiding Principle 4).
    """
    video_path = Path(input.video_path)

    # ── Guard: file must exist ─────────────────────────────────────────────
    if not video_path.exists():
        logger.error("Video not found: %s", video_path)
        return VideoFindings(errors=[f"Video file not found: {video_path}"])

    errors: list[str] = []
    fps = _get_fps(video_path)

    # ── Phase 1: Extraction ────────────────────────────────────────────────
    try:
        snippet_metas = extract_snippets(video_path)
    except Exception as exc:
        logger.exception("Extraction failed for %s", video_path)
        return VideoFindings(errors=[f"Extraction failed: {exc}"])

    face_roi_count = sum(len(m.face_crop_paths) for m in snippet_metas)

    if face_roi_count == 0:
        msg = (
            "No face detected in any snippet — tri-stream analysis cannot run. "
            "All forensic streams will be NOT_ASSESSED."
        )
        logger.warning(msg)
        errors.append(msg)

    all_crop_paths = [
        path
        for meta in snippet_metas
        for path in meta.face_crop_paths
    ]

    # ── Phase 2: Spectral stream ───────────────────────────────────────────
    spectral_results: list[SpectralResult] = []
    for crop_path in all_crop_paths:
        try:
            spectral_results.append(analyze_spectral(crop_path))
        except Exception as exc:
            logger.warning("Spectral failed on %s: %s", crop_path, exc)
            errors.append(f"Spectral error on {Path(crop_path).name}: {exc}")

    spectral_agg = aggregate_spectral(spectral_results) if spectral_results else _NOT_ASSESSED_SPECTRAL

    # ── Phase 2: rPPG stream ───────────────────────────────────────────────
    try:
        rppg_result = analyze_rppg(video_path, snippet_metas, fps)
    except Exception as exc:
        logger.warning("rPPG analysis failed: %s", exc)
        errors.append(f"rPPG error: {exc}")
        rppg_result = _NOT_ASSESSED_RPPG

    # ── Phase 2: Per-frame Module 2 stub calls ─────────────────────────────
    frame_analyses: list[dict] = []
    if analyze_image_fn is not None and all_crop_paths:
        for crop_path in all_crop_paths:
            try:
                findings = analyze_image_fn(crop_path, input.claim_text)
                frame_analyses.append(findings.model_dump())
            except Exception as exc:
                logger.warning("analyze_image_fn failed on %s: %s", crop_path, exc)
                errors.append(f"Frame analysis error on {Path(crop_path).name}: {exc}")

    # ── Phase 3: Spatial stream (ViT + attention rollout) ──────────────────
    spatial_results: list[SpatialResult] = []
    for crop_path in all_crop_paths:
        try:
            spatial_results.append(analyze_spatial(crop_path))
        except Exception as exc:
            logger.warning("Spatial failed on %s: %s", crop_path, exc)
            errors.append(f"Spatial error on {Path(crop_path).name}: {exc}")

    spatial_agg = aggregate_spatial(spatial_results) if spatial_results else _NOT_ASSESSED_SPATIAL

    # ── Phase 3: Weighted-peak fusion ──────────────────────────────────────
    try:
        fusion_out = fuse(spectral_agg, rppg_result, spatial_agg, snippet_metas, fps)
    except Exception as exc:
        logger.exception("Fusion failed: %s", exc)
        errors.append(f"Fusion error: {exc}")
        # Return what we have without verdict
        return VideoFindings(
            extraction_meta=snippet_metas,
            face_roi_count=face_roi_count,
            frame_analyses=frame_analyses,
            errors=errors,
        )

    # ── Phase 2: Module 5 reuse stub (keyframe historical lookup) ──────────
    # Called per-snippet for keyframe-level historical reuse coverage (guide B7).
    # Stub returns empty ReuseFindings; swap reuse_lookup_fn when Person 1 ships.
    if reuse_lookup_fn is not None and all_crop_paths:
        for crop_path in all_crop_paths[:3]:   # limit to first 3 crops for the demo
            try:
                reuse_lookup_fn(crop_path)     # result unused until Module 7 consumes it
            except Exception as exc:
                logger.warning("Reuse lookup failed on %s: %s", crop_path, exc)

    logger.info(
        "Module 3 complete | verdict=%s confidence=%s errors=%d",
        fusion_out["verdict"],
        fusion_out["confidence_score"],
        len(errors),
    )

    return VideoFindings(
        extraction_meta=snippet_metas,
        face_roi_count=face_roi_count,
        verdict=fusion_out["verdict"],
        confidence_score=fusion_out["confidence_score"],
        forensic_streams=fusion_out["forensic_streams"],
        flagged_segments_sec=fusion_out["flagged_segments_sec"],
        concrete_evidence=fusion_out["concrete_evidence"],
        saliency_heatmap_path=fusion_out["saliency_heatmap_path"],
        frame_analyses=frame_analyses,
        errors=errors,
    )
