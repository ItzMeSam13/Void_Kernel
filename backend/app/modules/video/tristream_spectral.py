"""
Module 3 — Task 1: Frequency Domain Forensics (Spectral Stream).

Architecture fix (architecture.md Module 3 §3 [fix]):
  The original spec's single `spectral_artifact_detected` is REPLACED by two
  independent sub-features derived from the same 2D-DCT output:

  spectral_artifact_score:
    Measures energy concentrated in a PERIODIC / CHECKERBOARD pattern at
    frequencies tied to a generator's upsampling stride.
    → GAN/diffusion synthesis evidence (Deliverable 4 — media authenticity axis).

  signal_integrity_score:
    Measures BROADBAND, NON-PERIODIC high-frequency energy — the signature of
    recompression, re-encoding, or adversarial noise, none of which imply
    synthetic content.
    → confidence caveat on the authenticity axis, drives adversarial_status,
      NEVER used as evidence of AI generation (Deliverable 6).

Confound rule (Guiding Principle 4 — fail honest, not silent):
  When signal_integrity_score is high AND spectral_artifact_score would
  otherwise register as a hit, set confounded_by_recompression=True and
  downgrade spectral_stream_verdict to INCONCLUSIVE. Without this split, an
  ordinary reposted / re-encoded real video raises broadband high-frequency
  energy and would be misread as "AI-generated".
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# Resize before DCT for consistent frequency bins across any source resolution.
_DCT_SIZE = 128

# Fraction of image height/width treated as "high-frequency corner".
_HF_MARGIN = 0.25

# Score thresholds (empirically tuned; can be adjusted once a labeled set exists).
_SPECTRAL_HIT_THRESHOLD = 0.60
_SPECTRAL_CLEAR_THRESHOLD = 0.25
_SIGNAL_INTEGRITY_CONFOUND_THRESHOLD = 0.55


# ---------------------------------------------------------------------------
# Data class
# ---------------------------------------------------------------------------

@dataclass
class SpectralResult:
    spectral_artifact_score: float   # [0, 1] — periodic energy
    signal_integrity_score: float    # [0, 1] — broadband energy
    confounded_by_recompression: bool
    stream_verdict: str              # one of the StreamVerdict string values


# ---------------------------------------------------------------------------
# Core DCT analysis
# ---------------------------------------------------------------------------

def _compute_dct_features(gray: np.ndarray) -> tuple[float, float]:
    """
    Returns (spectral_artifact_score, signal_integrity_score).

    spectral_artifact_score — periodicty in the high-freq corner:
      Apply 2D-FFT to the DCT's high-frequency corner block.
      GAN/diffusion upsampling leaves energy at specific stride-related
      frequencies → strong off-centre peaks in this 2nd-order transform.
      Score = (peak / mean) ratio, normalised to [0, 1].

    signal_integrity_score — overall broadband corner energy:
      Total energy in the high-frequency DCT corners, normalised by the DC
      component. High → recompression/noise (JPEG artefacts, re-encoding).
    """
    h, w = gray.shape
    gray_f32 = gray.astype(np.float32)
    dct = cv2.dct(gray_f32)

    mh = int(h * _HF_MARGIN)
    mw = int(w * _HF_MARGIN)

    # Three high-frequency corners (exclude top-left which is just mid-freq).
    corners = np.concatenate([
        dct[:mh, -mw:].ravel(),
        dct[-mh:, :mw].ravel(),
        dct[-mh:, -mw:].ravel(),
    ])

    if corners.size == 0:
        return 0.0, 0.0

    # ---- signal_integrity_score (broadband) --------------------------------
    dc_energy = float(dct[0, 0] ** 2) + 1e-8
    hf_energy = float(np.sum(corners ** 2))
    # Empirical divisor: keeps typical JPEG-compressed real photos around 0.2–0.4.
    signal_integrity_score = float(np.clip(hf_energy / (dc_energy * 6.0), 0.0, 1.0))

    # ---- spectral_artifact_score (periodic) --------------------------------
    # Apply 2D-FFT to the bottom-right corner block.
    corner_block = dct[-mh:, -mw:]
    fft2 = np.abs(np.fft.fft2(corner_block))
    fft2_shifted = np.fft.fftshift(fft2)

    # Zero out the DC of this 2nd-order transform so we only measure off-centre peaks.
    cy, cx = fft2_shifted.shape[0] // 2, fft2_shifted.shape[1] // 2
    r = max(1, min(cy, cx) // 4)
    fft2_shifted[cy - r: cy + r, cx - r: cx + r] = 0.0

    mean_e = float(np.mean(fft2_shifted)) + 1e-8
    peak_e = float(np.max(fft2_shifted))
    # Typical noise gives a ratio of ~5–10; a GAN grid pushes this to >20.
    periodicity_ratio = peak_e / mean_e
    spectral_artifact_score = float(np.clip((periodicity_ratio - 5.0) / 25.0, 0.0, 1.0))

    return spectral_artifact_score, signal_integrity_score


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def analyze_spectral(face_crop_path: str) -> SpectralResult:
    """
    Run spectral analysis on one saved face crop.
    Returns SpectralResult with per-sub-feature scores and confound flag.
    """
    img = cv2.imread(face_crop_path)
    if img is None:
        logger.warning("Spectral: could not read crop %s — returning not_assessed.", face_crop_path)
        return SpectralResult(0.0, 0.0, False, "not_assessed")

    img_r = cv2.resize(img, (_DCT_SIZE, _DCT_SIZE))
    gray = cv2.cvtColor(img_r, cv2.COLOR_BGR2GRAY)

    sa_score, si_score = _compute_dct_features(gray)

    confounded = (
        si_score > _SIGNAL_INTEGRITY_CONFOUND_THRESHOLD
        and sa_score >= _SPECTRAL_HIT_THRESHOLD
    )

    if confounded:
        verdict = "inconclusive"
    elif sa_score >= _SPECTRAL_HIT_THRESHOLD:
        verdict = "signal_detected"
    elif sa_score <= _SPECTRAL_CLEAR_THRESHOLD:
        verdict = "no_strong_signal_detected"
    else:
        verdict = "inconclusive"

    return SpectralResult(
        spectral_artifact_score=round(sa_score, 4),
        signal_integrity_score=round(si_score, 4),
        confounded_by_recompression=confounded,
        stream_verdict=verdict,
    )


def aggregate_spectral(results: list[SpectralResult]) -> SpectralResult:
    """
    Aggregate per-crop results across all snippets using weighted-peak logic:
    forward the crop with highest spectral_artifact_score; average signal_integrity.
    """
    valid = [r for r in results if r.stream_verdict != "not_assessed"]
    if not valid:
        return SpectralResult(0.0, 0.0, False, "not_assessed")

    peak = max(valid, key=lambda r: r.spectral_artifact_score)
    avg_si = float(np.mean([r.signal_integrity_score for r in valid]))

    return SpectralResult(
        spectral_artifact_score=peak.spectral_artifact_score,
        signal_integrity_score=round(avg_si, 4),
        confounded_by_recompression=peak.confounded_by_recompression,
        stream_verdict=peak.stream_verdict,
    )
