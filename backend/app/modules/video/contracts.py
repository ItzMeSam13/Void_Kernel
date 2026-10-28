"""
modules/video/contracts.py -- Module 3 public contracts (Person 2 owns this).

VideoInput / VideoFindings form the ONLY interface surface of Module 3.
Matches video_forensics_tech_spec.md §4 plus the spectral split fix
(architecture.md §Module 3).

Architecture rule (§6): this file may be imported with ZERO other modules
or orchestration packages on the Python path (except app.orchestrator.enums).

IMPORTANT -- spectral split (architecture.md Module 3 + Module 7):
  spectral_artifact_score      -- periodic GAN/diffusion evidence -> authenticity axis
  signal_integrity_score       -- broadband recompression -> confidence modifier
  confounded_by_recompression  -- true when signal_integrity_score is high
"""
from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any, Optional, Union

from pydantic import BaseModel, Field, model_validator

from app.orchestrator.enums import Verdict


# ---------------------------------------------------------------------------
# Shared enumerations
# ---------------------------------------------------------------------------

class StreamVerdict(str, Enum):
    SIGNAL_DETECTED = "signal_detected"
    NO_STRONG_SIGNAL = "no_strong_signal_detected"
    INCONCLUSIVE = "inconclusive"
    NOT_ASSESSED = "not_assessed"


# ---------------------------------------------------------------------------
# Input contract
# ---------------------------------------------------------------------------

class VideoInput(BaseModel):
    """Input to Module 3's run() entrypoint."""

    video_path: Optional[Union[str, Path]] = Field(
        default=None,
        description="Local path (.mp4 / .mov / .avi) to the video file to analyse.",
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
        description="Paths to saved padded face-crop images for this snippet.",
    )
    keyframe_path: Optional[str] = Field(
        default=None,
        description="Path to the full uncropped representative frame for this snippet.",
    )
    timestamp_sec: Optional[float] = Field(
        default=None,
        description="Timestamp in seconds for the start of this snippet.",
    )


# ---------------------------------------------------------------------------
# Tri-stream forensic scores (Phase 2/3)
# ---------------------------------------------------------------------------

class ForensicStreams(BaseModel):
    """
    Scores from the three forensic streams.

    Architecture fix (architecture.md Module 3 §3):
      spectral_artifact_score   -> periodic / checkerboard energy -> AI-generation evidence
      signal_integrity_score    -> broadband / non-periodic energy -> recompression evidence
      confounded_by_recompression -> True when signal_integrity_score is high enough to
                                    invalidate a confident spectral_artifact_score verdict
    """

    # Spatial stream (ViT + attention rollout)
    spatial_anomaly_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="ViT patch-level anomaly score [0-1].",
    )
    spatial_localization: Optional[str] = Field(
        default=None,
        description='Human-readable landmark region, e.g. "lower chin boundary".',
    )
    spatial_stream_verdict: StreamVerdict = Field(
        default=StreamVerdict.NOT_ASSESSED,
        description="Rolled-up verdict for the spatial stream.",
    )

    # Spectral stream (2D-DCT energy split)
    spectral_artifact_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Periodic checkerboard energy -> GAN/diffusion evidence.",
    )
    signal_integrity_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Broadband non-periodic HF energy -> recompression caveat.",
    )
    confounded_by_recompression: bool = Field(
        default=False,
        description="True when signal_integrity_score is high enough to invalidate spectral score.",
    )
    spectral_stream_verdict: StreamVerdict = Field(
        default=StreamVerdict.NOT_ASSESSED,
        description="Rolled-up verdict for the spectral stream.",
    )

    # rPPG biometric stream
    biometric_pulse_detected: Optional[bool] = Field(
        default=None,
        description="True if a physiologically plausible rPPG signal (0.7-2.5 Hz) is found.",
    )
    rppg_peak_hz: Optional[float] = Field(
        default=None,
        description="Dominant FFT peak frequency in Hz, or None if no clear peak.",
    )
    rppg_stream_verdict: StreamVerdict = Field(
        default=StreamVerdict.NOT_ASSESSED,
        description="Rolled-up verdict for the rPPG stream.",
    )

    # Adversarial status
    adversarial_status: Optional[str] = Field(
        default=None,
        description="Human-readable adversarial-perturbation note.",
    )


# ---------------------------------------------------------------------------
# Full output contract
# ---------------------------------------------------------------------------

class VideoFindings(BaseModel):
    """
    Output of Module 3's run() entrypoint.
    Matches the stub in orchestrator/state.py and supports rich forensics.
    """

    modality: str = Field(default="video_deepfake_engine")

    # Phase 1 fields
    extraction_meta: list[SnippetMeta] = Field(
        default_factory=list,
        description="Per-snippet extraction + face detection metadata.",
    )
    face_roi_count: int = Field(
        default=0,
        description="Total number of face ROI images extracted across all snippets.",
    )

    # Verdict & Confidence
    verdict: Verdict = Field(
        default=Verdict.NOT_ASSESSED,
        description="Overall deepfake verdict.",
    )
    confidence_score: Optional[float] = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Fused confidence [0-1].",
    )

    # Structured tri-stream scores
    forensic_streams: ForensicStreams = Field(
        default_factory=ForensicStreams,
        description="Per-stream scores.",
    )

    # Flattened spectral split & stream fields (for Module 7 / state.py direct access)
    spectral_artifact_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Periodic checkerboard energy -> GAN/diffusion evidence.",
    )
    signal_integrity_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Broadband non-periodic HF energy -> recompression caveat.",
    )
    confounded_by_recompression: bool = Field(
        default=False,
        description="True when signal_integrity_score is high.",
    )
    spatial_anomaly_description: Optional[str] = Field(
        default=None,
        description="Human-readable spatial anomaly description.",
    )
    rppg_signal_present: Optional[bool] = Field(
        default=None,
        description="True if physiological blood volume pulse detected.",
    )
    adversarial_status: Optional[str] = Field(
        default=None,
        description="Human-readable adversarial status string.",
    )

    # Evidence & saliency
    flagged_segments_sec: list[Any] = Field(
        default_factory=list,
        description="Video timestamps (seconds) where anomalies were detected.",
    )
    concrete_evidence: list[str] = Field(
        default_factory=list,
        description="Human-readable evidence strings passed directly into Module 7.",
    )
    saliency_heatmap_path: Optional[str] = Field(
        default=None,
        description="Path to attention-rollout overlay image.",
    )

    # Frame analyses from Module 2
    frame_analyses: list[dict] = Field(
        default_factory=list,
        description="Results of Module 2's analyze_image() called on each sampled frame.",
    )

    # Errors
    errors: list[str] = Field(
        default_factory=list,
        description="Non-fatal errors encountered during processing.",
    )
    error: Optional[str] = Field(
        default=None,
        description="Top-level error message if processing failed.",
    )

    @model_validator(mode="before")
    @classmethod
    def _sync_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        # Sync from forensic_streams to flat fields
        streams = data.get("forensic_streams")
        if isinstance(streams, ForensicStreams):
            if data.get("spectral_artifact_score") is None:
                data["spectral_artifact_score"] = streams.spectral_artifact_score
            if data.get("signal_integrity_score") is None:
                data["signal_integrity_score"] = streams.signal_integrity_score
            if "confounded_by_recompression" not in data or data["confounded_by_recompression"] is False:
                data["confounded_by_recompression"] = streams.confounded_by_recompression
            if data.get("spatial_anomaly_description") is None:
                data["spatial_anomaly_description"] = streams.spatial_localization
            if data.get("rppg_signal_present") is None:
                data["rppg_signal_present"] = streams.biometric_pulse_detected
            if data.get("adversarial_status") is None:
                data["adversarial_status"] = streams.adversarial_status
        elif isinstance(streams, dict):
            if data.get("spectral_artifact_score") is None:
                data["spectral_artifact_score"] = streams.get("spectral_artifact_score")
            if data.get("signal_integrity_score") is None:
                data["signal_integrity_score"] = streams.get("signal_integrity_score")
            if "confounded_by_recompression" not in data or data["confounded_by_recompression"] is False:
                data["confounded_by_recompression"] = streams.get("confounded_by_recompression", False)
            if data.get("spatial_anomaly_description") is None:
                data["spatial_anomaly_description"] = streams.get("spatial_localization")
            if data.get("rppg_signal_present") is None:
                data["rppg_signal_present"] = streams.get("biometric_pulse_detected")
            if data.get("adversarial_status") is None:
                data["adversarial_status"] = streams.get("adversarial_status")

        # Sync error string
        err = data.get("error")
        errors = data.get("errors") or []
        if err and not errors:
            data["errors"] = [err]
        elif errors and not err:
            data["error"] = "; ".join(errors)

        return data
