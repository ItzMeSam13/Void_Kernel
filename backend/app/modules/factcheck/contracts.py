"""
modules/factcheck/contracts.py — Module 6 public contracts (Person 1A owns this).

FactCheckInput / ClaimFindings form the ONLY interface surface of Module 6.

SCOPE NOTE (architecture.md §6 step 3):
  The per-claim Send fan-out (Veritas pattern) is implemented INSIDE this
  module's own LangGraph subgraph.  The top-level orchestrator (pipeline.py)
  calls run() as a black box and does NOT know about per-claim fan-out.
"""
from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field

from app.orchestrator.enums import Verdict


class FactCheckInput(BaseModel):
    """
    Input to Module 6's run() entrypoint.
    The orchestrator passes image/reuse findings so Module 6 can
    incorporate entity-level cross-modal consistency checks.
    """
    claim_text:      Optional[str]  = Field(None,
        description="Claim text from caption, OCR, or Whisper transcript.")
    # Source provenance from Module 5 (for entity-level cross-check)
    image_findings:  Optional[Any]  = Field(None,
        description="ImageFindings from Module 2 (for OCR context).")
    reuse_findings:  Optional[Any]  = Field(None,
        description="ReuseFindings from Module 5 (source date/location for entity cross-check).")


class ClaimFindings(BaseModel):
    """
    Output of Module 6's run() entrypoint.
    Matches the stub in orchestrator/state.py — keep in sync.
    """
    claims_assessed:         list[str]           = Field(default_factory=list,
        description="List of atomic claim strings that were fact-checked.")
    overall_verdict:         Verdict             = Verdict.NOT_ASSESSED
    overall_confidence:      float               = Field(0.0, ge=0.0, le=1.0)
    evidence_items:          list[dict[str, Any]] = Field(default_factory=list,
        description="Raw evidence dicts: {source_url, stance, relevance_score, snippet}.")
    entity_agreement_matrix: dict[str, Any]      = Field(default_factory=dict,
        description="Per-entity cross-signal agreement flags from entity × signal check.")
    echo_chamber_flag:       bool                = False
    drift_guard_similarity:  Optional[float]     = Field(None,
        description="Cosine similarity between original input and recomposed claims.")
    error:                   Optional[str]       = None
