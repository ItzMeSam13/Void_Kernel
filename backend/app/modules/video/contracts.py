"""
Module 3 — Video Intelligence: Pydantic I/O contracts.

Architecture rule (§6): this file may be imported with ZERO other modules
or orchestration packages on the Python path. No cross-module imports.

Output schema deliberately deviates from video_forensics_tech_spec.md §4
in one place (architecture.md Module 3 [fix]):
  - `spectral_artifact_detected: bool` is REPLACED by
      spectral_artifact_score: float | None
      signal_integrity_score:   float | None
      confounded_by_recompression: bool
  - `adversarial_status` is driven only by signal_integrity_score, not by
    spectral energy (which is about AI-generation, not adversarial noise).

Every other field from the spec carries over unchanged so teammates can
parse this output without any contract surprises.

Phase 1 populates: extraction_meta, face_roi_count, flagged_segments_sec
                   (empty list until tri-stream runs), modality.
Phase 2 populates: forensic_streams.* (scores), concrete_evidence[].
Phase 3 populates: verdict, confidence_score, saliency_heatmap_path,
                   frame_analyses (Module 2 per-frame results).
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Shared enumerations
# ---------------------------------------------------------------------------

class Verdict(str, Enum):
    FAKE = "FAKE"
    REAL = "REAL"
    INCONCLUSIVE = "INCONCLUSIVE"
    NOT_ASSESSED = "NOT_ASSESSED"


class StreamVerdict(str, Enum):
    SIGNAL_DETECTED = "signal_detected"
    NO_STRONG_SIGNAL = "no_strong_signal_detected"
    INCONCLUSIVE = "inconclusive"
    NOT_ASSESSED = "not_assessed"


# ---------------------------------------------------------------------------
# Input contract
# ---------------------------------------------------------------------------

class VideoInput(BaseModel):
    """Single video file submitted for analysis."""

    video_path: Path = Field(
        ...,
        description="Absolute path to the .mp4 / .mov / .avi file to analyse.",
    )
    claim_text: Optional[str] = Field(
        default=None,
        description=(
            "User-supplied caption or claim about this video. "
            "Passed through to Module 2's analyze_image() per-frame call in Phase 2."
        ),
    )


# ---------------------------------------------------------------------------
# Per-snippet extraction metadata (Phase 1)
# ---------------------------------------------------------------------------

class SnippetMeta(BaseModel):
    """Metadata for one 30-frame dense snippet."""

    snippet_index: int = Field(..., description="0, 1, or 2 (10 / 50 / 90% position).")
    start_frame: int = Field(..., description="First frame index extracted from the video.")
    end_frame: int = Field(..., description="Last frame index extracted (inclusive).")
    position_pct: float = Field(..., description="Relative position in the video (0.10, 0.50, 0.90).")
    face_detected: bool = Field(
        default=False,
        description="True if MediaPipe FaceMesh found at least one face in this snippet.",
    )
    face_crop_paths: list[str] = Field(
        default_factory=list,
        description="Paths to saved padded face-crop images for this snippet (written to /tmp/).",
    )


# ---------------------------------------------------------------------------
# Tri-stream forensic scores (Phase 2/3 — None until those phases run)
# ---------------------------------------------------------------------------

class ForensicStreams(BaseModel):
    """
    Scores from the three forensic streams.

    Architecture fix (architecture.md Module 3 §3):
      spectral_artifact_score   → periodic / checkerboard energy → AI-generation evidence
      signal_integrity_score    → broadband / non-periodic energy → recompression evidence
      confounded_by_recompression → True when signal_integrity_score is high enough to
                                    invalidate a confident spectral_artifact_score verdict
    """

    # Spatial stream (Phase 3 — ViT + attention rollout)
    spatial_anomaly_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="ViT patch-level anomaly score [0–1]. None until Phase 3.",
    )
    spatial_localization: Optional[str] = Field(
        default=None,
        description=(
            'Human-readable landmark region, e.g. "lower chin boundary". '
            "None until Phase 3."
        ),
    )

    # Spectral stream — split into two sub-features (Phase 2)
    spectral_artifact_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description=(
            "Periodic / checkerboard DCT corner-energy score [0–1]. "
            "High → AI upsampling evidence (Deliverable 4). None until Phase 2."
        ),
    )
    signal_integrity_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description=(
            "Broadband / non-periodic high-frequency energy score [0–1]. "
            "High → recompression / re-encoding / adversarial noise evidence "
            "(Deliverable 6). Drives adversarial_status, NOT spectral_artifact_score. "
            "None until Phase 2."
        ),
    )
    confounded_by_recompression: bool = Field(
        default=False,
        description=(
            "True when signal_integrity_score is high enough to invalidate a "
            "confident spectral_artifact_score verdict. When True, spectral verdict "
            "is downgraded to INCONCLUSIVE per architecture.md Guiding Principle 4."
        ),
    )
    spectral_stream_verdict: StreamVerdict = Field(
        default=StreamVerdict.NOT_ASSESSED,
        description="Rolled-up verdict for the spectral stream.",
    )

    # rPPG biometric stream (Phase 2)
    biometric_pulse_detected: Optional[bool] = Field(
        default=None,
        description=(
            "True if a physiologically plausible rPPG signal (0.7–2.5 Hz) "
            "is found in the forehead green channel. False → biologically dead → "
            "deepfake evidence. None until Phase 2."
        ),
    )
    rppg_peak_hz: Optional[float] = Field(
        default=None,
        description="Dominant FFT peak frequency in Hz, or None if no clear peak. None until Phase 2.",
    )
    rppg_stream_verdict: StreamVerdict = Field(
        default=StreamVerdict.NOT_ASSESSED,
        description="Rolled-up verdict for the rPPG stream.",
    )

    # Adversarial status — driven ONLY by signal_integrity_score (not spectral)
    adversarial_status: Optional[str] = Field(
        default=None,
        description=(
            "Human-readable adversarial-perturbation note, e.g. "
            "'HIGH-FREQUENCY PERTURBATION DETECTED'. Populated only when "
            "signal_integrity_score is high. None until Phase 2."
        ),
    )


# ---------------------------------------------------------------------------
# Full output contract
# ---------------------------------------------------------------------------

class VideoFindings(BaseModel):
    """
    Module 3 output consumed by:
      - Module 7 (Person 1): `concrete_evidence[]`, `forensic_streams.*`, `verdict`
      - Module 5 (Person 1): keyframe paths for historical-reuse lookup
      - Module 2 (Person 3): called per-frame; results stored in `frame_analyses`
      - SyncNet (stretch, Phase 4): `flagged_segments_sec`

    Contract boundary (architecture.md [Improvement]):
      `verdict` answers ONLY "was this synthetically generated?"
      It NEVER answers "has this been seen before?" — that is Module 5's job.
    """

    modality: str = Field(default="video_deepfake_engine", frozen=True)

    # Phase 1 fields — populated immediately
    extraction_meta: list[SnippetMeta] = Field(
        default_factory=list,
        description="Per-snippet extraction + face detection metadata.",
    )
    face_roi_count: int = Field(
        default=0,
        description="Total number of face ROI images extracted across all snippets.",
    )

    # Phase 2/3 fields — None / empty until those phases run
    verdict: Verdict = Field(
        default=Verdict.NOT_ASSESSED,
        description="Overall deepfake verdict. NOT_ASSESSED until Phase 3 fusion runs.",
    )
    confidence_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Fused confidence [0–1]. None until Phase 3.",
    )
    forensic_streams: ForensicStreams = Field(
        default_factory=ForensicStreams,
        description="Per-stream scores. All sub-fields None until Phase 2/3.",
    )
    flagged_segments_sec: list[float] = Field(
        default_factory=list,
        description=(
            "Video timestamps (seconds) where anomalies were detected. "
            "Consumed by Module 4's optional SyncNet cross-check. "
            "Empty until Phase 3."
        ),
    )
    concrete_evidence: list[str] = Field(
        default_factory=list,
        description=(
            "Human-readable evidence strings passed directly into Module 7's "
            "explanation prompt (video_forensics_tech_spec.md §5). "
            "Empty until Phase 2/3."
        ),
    )
    saliency_heatmap_path: Optional[str] = Field(
        default=None,
        description="Path to the attention-rollout overlay image. None until Phase 3.",
    )

    # Phase 2 — per-frame Module 2 results (any JSON-serialisable dict from ImageFindings)
    frame_analyses: list[dict] = Field(
        default_factory=list,
        description=(
            "Results of Module 2's analyze_image() called on each sampled frame. "
            "Typed as dict to avoid a cross-module import — Person 3's ImageFindings "
            "schema is the exact shape expected here. Empty until Phase 2."
        ),
    )

    # Error / partial-failure reporting (Guiding Principle 4: fail honest, not silent)
    errors: list[str] = Field(
        default_factory=list,
        description=(
            "Non-fatal errors encountered during processing "
            "(e.g. no face detected in a snippet, model load failure). "
            "A non-empty list does NOT make the whole finding invalid — "
            "it flags which streams are missing and why."
        ),
    )
