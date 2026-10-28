"""
Module 3 — Stage 4: Multi-Stream Weighted-Peak Fusion.

Fuses spectral + rPPG + spatial stream results into the full JSON contract
defined in video_forensics_tech_spec.md §4, with the architecture deviations
documented in architecture.md Module 3 §5.

Weighted-peak fusion (per spec §4, "favoring highest peak anomaly, not average"):
  Each stream contributes a weighted score. The final confidence is driven by
  the MAXIMUM weighted contribution rather than the mean — one strong stream
  is sufficient evidence; it isn't diluted by weaker streams.
  A 15% bonus is added when ≥ 2 streams independently agree (signal convergence).

adversarial_status:
  Driven ONLY by signal_integrity_score (broadband / recompression evidence),
  NOT by spectral_artifact_score. This is the architecture fix that prevents
  "AI-generated" and "adversarially perturbed" from being two claims backed by
  the same DCT measurement.

Architecture contract deviation from spec as written:
  forensic_streams.spectral_artifact_detected (bool) is ABSENT.
  Replaced by:
    spectral_artifact_score     (float)
    signal_integrity_score      (float)
    confounded_by_recompression (bool)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from app.modules.video.contracts import (
    ForensicStreams,
    StreamVerdict,
    Verdict,
)
from app.modules.video.tristream_spectral import SpectralResult
from app.modules.video.tristream_rppg import RppgResult
from app.modules.video.tristream_spatial import SpatialResult

logger = logging.getLogger(__name__)

# Stream weights — spatial is highest (most direct evidence of face-swap seam).
_W_SPATIAL = 0.45
_W_SPECTRAL = 0.35
_W_RPPG = 0.20

_FAKE_THRESHOLD = 0.62
_REAL_THRESHOLD = 0.30
_SIGNAL_INTEGRITY_ADVERSARIAL_THRESHOLD = 0.60


def _norm_score(raw: float, weight: float) -> float:
    """Normalised weighted score in [0, 1]."""
    return float(min(1.0, raw * weight / max(_W_SPATIAL, _W_SPECTRAL, _W_RPPG)))


def _build_forensic_streams(
    spectral: SpectralResult,
    rppg: RppgResult,
    spatial: SpatialResult,
) -> ForensicStreams:
    """Populate the full ForensicStreams model from per-stream results."""
    adversarial_status = None
    if (
        spectral.signal_integrity_score is not None
        and spectral.signal_integrity_score > _SIGNAL_INTEGRITY_ADVERSARIAL_THRESHOLD
    ):
        adversarial_status = "HIGH-FREQUENCY PERTURBATION DETECTED"

    return ForensicStreams(
        # Spatial
        spatial_anomaly_score=spatial.spatial_anomaly_score,
        spatial_localization=spatial.spatial_localization,
        # Spectral — two sub-features (architecture fix)
        spectral_artifact_score=spectral.spectral_artifact_score,
        signal_integrity_score=spectral.signal_integrity_score,
        confounded_by_recompression=spectral.confounded_by_recompression,
        spectral_stream_verdict=StreamVerdict(spectral.stream_verdict),
        # rPPG
        biometric_pulse_detected=rppg.biometric_pulse_detected,
        rppg_peak_hz=rppg.rppg_peak_hz,
        rppg_stream_verdict=StreamVerdict(rppg.stream_verdict),
        # Adversarial status — riven by signal_integrity only
        adversarial_status=adversarial_status,
    )


def _build_concrete_evidence(
    spectral: SpectralResult,
    rppg: RppgResult,
    spatial: SpatialResult,
    max_smaug_prob: Optional[float] = None,
) -> list[str]:
    """Build the concrete_evidence list consumed verbatim by Module 7's LLM prompt."""
    evidence: list[str] = []

    # rPPG (biometric)
    if rppg.biometric_pulse_detected is False:
        evidence.append(
            "Biometric anomaly: Lack of remote photoplethysmography (blood volume pulse) "
            "detected across frames — consistent with synthetically generated content."
        )
    elif rppg.biometric_pulse_detected is True:
        evidence.append(
            f"Biometric signal: Physiological pulse detected at "
            f"{rppg.rppg_peak_hz:.2f} Hz — consistent with real human skin."
        )

    # Spectral
    if spectral.confounded_by_recompression:
        evidence.append(
            "Spectral note: High-frequency DCT corner energy detected, but broadband "
            "(non-periodic) signal is also elevated — result is confounded by likely "
            "recompression or re-encoding; spectral verdict downgraded to inconclusive."
        )
    elif spectral.spectral_artifact_score is not None and spectral.spectral_artifact_score >= 0.60:
        evidence.append(
            "Spectral anomaly: High-frequency 2D-DCT periodic grid artefacts detected — "
            "consistent with AI upsampling strides (GAN or diffusion generator trace)."
        )

    # Spectral — signal integrity / adversarial
    if (
        spectral.signal_integrity_score is not None
        and spectral.signal_integrity_score > _SIGNAL_INTEGRITY_ADVERSARIAL_THRESHOLD
    ):
        evidence.append(
            "Signal integrity: Elevated broadband high-frequency energy detected — "
            "consistent with recompression, re-encoding, or adversarial perturbation "
            "(not itself evidence of AI generation)."
        )

    # Spatial
    if spatial.stream_verdict == "signal_detected" and spatial.spatial_anomaly_score is not None:
        loc = spatial.spatial_localization or "facial boundary region"
        evidence.append(
            f"Spatial anomaly: Patch-level attention anomaly localised at the {loc} — "
            "consistent with face-swap blending seam."
        )

    # Smaug AI-generation signal from Module 2 keyframe analysis
    if max_smaug_prob is not None and max_smaug_prob >= 0.50:
        evidence.append(
            f"AI-generation evidence: Smaug detector flagged video keyframe as AI-generated "
            f"(probability: {max_smaug_prob:.2%}) — consistent with generative video synthesis."
        )

    return evidence


def _flagged_segments(
    spectral: SpectralResult,
    rppg: RppgResult,
    spatial: SpatialResult,
    snippet_metas,
    fps: float,
) -> list[float]:
    """
    Return start-timestamps (seconds) of snippets where any stream flagged a signal.
    Empty list means no specific segment was anomalous.
    """
    flagged: list[float] = []
    any_stream_hit = (
        spectral.stream_verdict == "signal_detected"
        or rppg.stream_verdict == "signal_detected"
        or spatial.stream_verdict == "signal_detected"
    )
    if any_stream_hit:
        for meta in snippet_metas:
            start_sec = round(meta.start_frame / fps, 2)
            flagged.append(start_sec)
    return flagged


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fuse(
    spectral: SpectralResult,
    rppg: RppgResult,
    spatial: SpatialResult,
    snippet_metas,
    fps: float,
    frame_analyses: Optional[list[dict]] = None,
) -> dict:
    """
    Multi-stream fusion integrating spectral, rPPG, spatial ViT streams,
    and Module 2 frame-level AI detection findings.
    """
    # ── 1. Extract raw stream scores ─────────────────────────────────────
    stream_scores: dict[str, float] = {}
    detected_flags: list[str] = []

    if spatial.spatial_anomaly_score is not None and spatial.stream_verdict != "not_assessed":
        stream_scores["spatial"] = spatial.spatial_anomaly_score
        if spatial.stream_verdict == "signal_detected" or spatial.spatial_anomaly_score >= 0.55:
            detected_flags.append("spatial")

    if spectral.stream_verdict != "not_assessed":
        sa = spectral.spectral_artifact_score
        if spectral.confounded_by_recompression:
            sa *= 0.6
        stream_scores["spectral"] = sa
        if spectral.stream_verdict == "signal_detected" and not spectral.confounded_by_recompression:
            detected_flags.append("spectral")

    if rppg.biometric_pulse_detected is not None:
        rppg_score = 0.88 if not rppg.biometric_pulse_detected else 0.05
        stream_scores["rppg"] = rppg_score
        if rppg.biometric_pulse_detected is False:
            detected_flags.append("rppg")

    # Module 2 Smaug signal across sampled keyframes
    max_smaug_prob: Optional[float] = None
    if frame_analyses:
        smaug_probs = [
            f.get("smaug", {}).get("ai_probability")
            for f in frame_analyses
            if f.get("smaug") and f.get("smaug", {}).get("ai_probability") is not None
        ]
        if smaug_probs:
            max_smaug_prob = max(smaug_probs)
            stream_scores["smaug"] = max_smaug_prob
            if max_smaug_prob >= 0.50:
                detected_flags.append("smaug")

    # ── 2. Verdict & Confidence Head ─────────────────────────────────────
    if not stream_scores:
        verdict = Verdict.NOT_ASSESSED
        confidence_score = None
    else:
        peak_score = max(stream_scores.values())
        num_detections = len(detected_flags)

        # Multi-signal convergence: >= 2 independent streams detecting anomalies
        # is strong convergence evidence (Guiding Principle 1 & spec §4).
        if num_detections >= 2:
            convergence_boost = 0.12 * (num_detections - 1)
            confidence_score = round(min(0.98, max(peak_score, 0.70) + convergence_boost), 4)
            verdict = Verdict.FAKE
        elif peak_score >= _FAKE_THRESHOLD or num_detections == 1:
            if peak_score >= 0.65:
                confidence_score = round(peak_score, 4)
                verdict = Verdict.FAKE
            else:
                confidence_score = round(peak_score, 4)
                verdict = Verdict.INCONCLUSIVE
        elif all(v <= _REAL_THRESHOLD for v in stream_scores.values()) and (
            rppg.biometric_pulse_detected is True or "rppg" not in stream_scores
        ):
            confidence_score = round(1.0 - peak_score, 4)
            verdict = Verdict.REAL
        else:
            confidence_score = round(peak_score, 4)
            verdict = Verdict.INCONCLUSIVE

    logger.info(
        "Fusion: verdict=%s confidence=%s detections=%s streams=%s",
        verdict, confidence_score, detected_flags, list(stream_scores.keys()),
    )

    return {
        "verdict": verdict,
        "confidence_score": confidence_score,
        "forensic_streams": _build_forensic_streams(spectral, rppg, spatial),
        "flagged_segments_sec": _flagged_segments(spectral, rppg, spatial, snippet_metas, fps),
        "concrete_evidence": _build_concrete_evidence(spectral, rppg, spatial, max_smaug_prob=max_smaug_prob),
        "saliency_heatmap_path": spatial.heatmap_path,
    }
