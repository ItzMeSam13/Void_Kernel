"""
modules/fusion/contracts.py — Module 7 public contracts.

FusionInput collects all per-module findings into one typed bundle that
Module 7's run() accepts.  FusionOutput and AxisResult live in
orchestrator/state.py so all modules can import them without circular deps.

Isolation rule (architecture.md §6): this file re-exports the canonical
types from their owners so callers need only one import.
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel

# ── Enums from the shared enum module ─────────────────────────────────────────
from app.orchestrator.enums import (     # noqa: F401
    Verdict,
    ConfidenceLevel,
)

# ── Findings from each module's canonical contracts ───────────────────────────
from app.modules.image.contracts import ImageFindings          # noqa: F401
from app.modules.video.contracts import VideoFindings          # noqa: F401
from app.modules.audio.contracts import AudioFindings          # noqa: F401
from app.modules.reuse.contracts import ReuseFindings          # noqa: F401
from app.modules.text.contracts import SyntheticTextFindings   # noqa: F401
from app.modules.factcheck.contracts import ClaimFindings      # noqa: F401

# ── Module 7 output (re-exported from state.py) ──────────────────────────────
from app.orchestrator.state import (     # noqa: F401
    FusionOutput,
    AxisResult,
)


class FusionInput(BaseModel):
    """
    All per-module findings assembled by the orchestrator before calling
    Module 7's run().  Every field is Optional — unavailable modules are
    represented as None, not as a missing field.
    """
    claim_text: Optional[str] = None

    # Module 2 (Person 3)
    image_findings: Optional[ImageFindings] = None

    # Module 3 (Person 2)
    video_findings: Optional[VideoFindings] = None

    # Module 4 (Person 3)
    audio_findings: Optional[AudioFindings] = None

    # Module 5 (Person 1 in-tree)
    reuse_findings: Optional[ReuseFindings] = None

    # Module 2B (Person 1 in-tree)
    synthetic_text_findings: Optional[SyntheticTextFindings] = None

    # Module 6 (Person 1A)
    claim_findings: Optional[ClaimFindings] = None
