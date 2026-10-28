"""
modules/video/contracts.py — Module 3 public contracts (Person 2 owns this).

VideoInput / VideoFindings form the ONLY interface surface of Module 3.
Matches video_forensics_tech_spec.md §4 plus the spectral split fix
(architecture.md §Module 3).

IMPORTANT — spectral split (architecture.md Module 3 + Module 7):
  spectral_artifact_score  — periodic GAN/diffusion evidence → authenticity axis
  signal_integrity_score   — broadband recompression → confidence modifier
  confounded_by_recompression — true when signal_integrity_score is high
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field

from app.orchestrator.enums import Verdict


class VideoInput(BaseModel):
    """Input to Module 3's run() entrypoint."""
    video_path:  Optional[str]  = Field(None, description="Local path to the video file.")
    claim_text:  Optional[str]  = Field(None, description="Caption or claim for cross-modal check.")


class VideoFindings(BaseModel):
    """
    Output of Module 3's run() entrypoint.
    Matches the stub in orchestrator/state.py — keep in sync.
    """
    verdict:          Verdict       = Verdict.NOT_ASSESSED
    confidence_score: float         = Field(0.0, ge=0.0, le=1.0)

    # ── Spectral split (architecture.md §Module 3 fix) ─────────────────────
    spectral_artifact_score:   Optional[float] = Field(None, ge=0.0, le=1.0,
        description="Periodic checkerboard energy → GAN/diffusion evidence (authenticity axis).")
    signal_integrity_score:    Optional[float] = Field(None, ge=0.0, le=1.0,
        description="Broadband non-periodic HF energy → recompression caveat (confidence modifier).")
    confounded_by_recompression: bool          = Field(False,
        description="True when signal_integrity_score is high; authenticity verdict degrades to INCONCLUSIVE.")

    # ── Other tri-stream outputs ───────────────────────────────────────────
    spatial_anomaly_description: Optional[str]                    = None
    rppg_signal_present:         Optional[bool]                   = None
    flagged_segments_sec:        list[tuple[float, float]]        = Field(default_factory=list)
    concrete_evidence:           list[str]                        = Field(default_factory=list,
        description="Human-readable strings fed directly to Module 7's explanation prompt.")
    saliency_heatmap_path:       Optional[str]                    = None
    adversarial_status:          Optional[str]                    = None
    error:                       Optional[str]                    = None
