"""
orchestrator/state.py — GraphState schema (Phase 3, contract-first)

This is the SINGLE source of truth for every field that flows through the
LangGraph StateGraph.

Shared enums live in orchestrator/enums.py (no circular import risk).
Per-module findings models live in each module's contracts.py and are
imported here — one canonical definition per type, no duplicates.

Rule (architecture.md §6): no module imports from this file.  The orchestrator
is the ONLY layer that imports both a module's contracts and GraphState.

Persons 1A / 2 / 3 each own their module's contracts.py.
──────────────────────────────────────────────────────────────────────────────
Axis naming convention (architecture.md §1 / Module 7):
  veracity      — claim factual truth (Module 6)
  authenticity  — media synthetic/manipulated (Modules 2, 3, 4)
  consistency   — cross-modal caption vs. image/audio (Modules 2, 3)
  reuse         — historical out-of-context reuse (Module 5)
──────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

from typing import Annotated, Any, Optional
from typing_extensions import TypedDict

from pydantic import BaseModel, Field
import operator

# ══════════════════════════════════════════════════════════════════════════════
# 1.  Shared enums (re-exported so existing `from state import Verdict` works)
# ══════════════════════════════════════════════════════════════════════════════

from app.orchestrator.enums import (       # noqa: F401 — re-export
    InputModality,
    Verdict,
    ConfidenceLevel,
)


# ══════════════════════════════════════════════════════════════════════════════
# 2.  Per-module findings — imported from each module's contracts.py
#     ONE canonical class per type.  No duplicates.
# ══════════════════════════════════════════════════════════════════════════════

from app.modules.factcheck.contracts import ClaimFindings     # noqa: F401
from app.modules.video.contracts import VideoFindings         # noqa: F401
from app.modules.image.contracts import ImageFindings         # noqa: F401
from app.modules.audio.contracts import AudioFindings         # noqa: F401
from app.modules.reuse.contracts import ReuseFindings         # noqa: F401
from app.modules.text.contracts import SyntheticTextFindings  # noqa: F401


# ══════════════════════════════════════════════════════════════════════════════
# 3.  Module 7 output (Person 1 — in-tree)
# ══════════════════════════════════════════════════════════════════════════════

class AxisResult(BaseModel):
    """Per-axis verdict + supporting evidence for Module 7's output."""
    verdict: Verdict = Verdict.NOT_ASSESSED
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    confidence_level: ConfidenceLevel = ConfidenceLevel.NONE
    evidence: list[str] = Field(default_factory=list,
        description="Traceable evidence strings shown verbatim in the report.")
    contributing_scores: dict[str, Any] = Field(default_factory=dict,
        description="Raw module scores that fed into this axis.")


class FusionOutput(BaseModel):
    """
    Module 7's complete output.  Four independent axes — never collapsed.
    """
    veracity:     AxisResult = Field(default_factory=AxisResult)
    authenticity: AxisResult = Field(default_factory=AxisResult)
    consistency:  AxisResult = Field(default_factory=AxisResult)
    reuse:        AxisResult = Field(default_factory=AxisResult)
    explanation:  Optional[str] = Field(None,
        description="3–4 sentence Gemini-generated evidence-grounded summary (Phase 3+).")
    short_label:  Optional[str] = None
    error:        Optional[str] = None


# ══════════════════════════════════════════════════════════════════════════════
# 4.  Top-level GraphState
#     LangGraph requires a TypedDict.  Pydantic models are stored as values.
#     The ``Annotated[list, operator.add]`` pattern gives LangGraph a reducer
#     for list fields that get appended by parallel branches.
# ══════════════════════════════════════════════════════════════════════════════

class GraphState(TypedDict, total=False):
    # ── Job identity ──────────────────────────────────────────────────────────
    job_id:       str
    sha256:       str                   # hex digest of raw upload bytes

    # ── Input ─────────────────────────────────────────────────────────────────
    modality:     InputModality         # set by router node
    content_type: Optional[str]         # MIME type from upload (e.g. "image/jpeg")
    claim_text:   Optional[str]         # user-supplied caption / claim
    media_path:   Optional[str]         # local temp path to uploaded file

    # ── Cache hit flag ────────────────────────────────────────────────────────
    cache_hit:    bool                  # True → skip all inference, return cached result

    # ── Per-module findings  (each branch writes its own field) ───────────────
    image_findings:         Optional[ImageFindings]
    video_findings:         Optional[VideoFindings]
    audio_findings:         Optional[AudioFindings]
    reuse_findings:         Optional[ReuseFindings]
    synthetic_text_findings: Optional[SyntheticTextFindings]
    claim_findings:         Optional[ClaimFindings]

    # ── Fusion output (Module 7) ──────────────────────────────────────────────
    fusion_output:          Optional[FusionOutput]

    # ── Errors / diagnostics accumulated across all branches ─────────────────
    errors: Annotated[list[str], operator.add]

    # ── Raw bytes (held in memory only during ingestion, not persisted) ───────
    _raw_bytes: Optional[bytes]
