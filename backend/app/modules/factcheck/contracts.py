"""
Module 6 — Fact-Checking & Evidence Engine
Pydantic contracts (input + output). No logic lives here.

Phase 1 scope (per team_roadmaps.md):
  - Claim splitter input/output
  - Adversarial Tavily search result
  - Evidence verdict per claim
  - ClaimFindings — the top-level output frozen at end of Phase 1

Phase 3 additions are marked [PHASE-3] (drift guard, echo-chamber,
NER entity-tagging, entity × signal agreement matrix).
"""
from __future__ import annotations

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ClaimType(str, Enum):
    FACT = "fact"
    FRAMING = "framing"
    ATTRIBUTED = "attributed"  # "X said Y"-style claim


class Stance(str, Enum):
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    NEUTRAL = "neutral"
    IRRELEVANT = "irrelevant"


class EvidenceVerdict(str, Enum):
    SUPPORTED = "supported"
    CONTRADICTED = "contradicted"
    UNCERTAIN = "uncertain"
    UNVERIFIABLE = "unverifiable"


class ClaimSource(str, Enum):
    CAPTION = "caption"          # raw input caption
    OCR = "ocr"                  # Module 2 PaddleOCR output
    TRANSCRIPT = "transcript"    # Module 4 Whisper output


# ---------------------------------------------------------------------------
# Atomic claim (output of claim splitter)
# ---------------------------------------------------------------------------

class AtomicClaim(BaseModel):
    """
    One atomic, checkable claim extracted from the input text.

    Phase 1: text + claim_type + loaded_language are populated (Veritas pattern).
    Phase 3 [PHASE-3]: location / datetime_ref / named_people / event_ref added
    via NER entity-tagging for the entity × signal agreement matrix.
    """
    claim_id: str = Field(description="Short UUID or index-based identifier, e.g. 'c1'.")
    text: str = Field(description="The atomic claim text.")
    claim_type: ClaimType

    # Veritas-ported fields
    loaded_language: list[str] = Field(
        default_factory=list,
        description="Emotionally loaded or evaluative terms extracted from the claim.",
    )

    # [PHASE-3] NER entity fields — all None in Phase 1
    location: Optional[str] = None
    datetime_ref: Optional[str] = None   # e.g. "yesterday", "2019-03-15"
    named_people: list[str] = Field(default_factory=list)
    event_ref: Optional[str] = None


# ---------------------------------------------------------------------------
# Evidence item (one search result / fact-check hit evaluated by the judge)
# ---------------------------------------------------------------------------

class EvidenceItem(BaseModel):
    """One piece of evidence evaluated against a single atomic claim."""
    source_url: str
    source_title: Optional[str] = None
    snippet: str = Field(description="The relevant excerpt from the source.")
    stance: Stance
    relevance_score: float = Field(ge=0.0, le=1.0)
    source_type: str = Field(
        description="E.g. 'tavily_confirming', 'tavily_contradicting', 'google_fact_check'.",
    )

    # [PHASE-3] echo-chamber flag
    echo_chamber_flagged: bool = False


# ---------------------------------------------------------------------------
# Per-claim finding
# ---------------------------------------------------------------------------

class SingleClaimFinding(BaseModel):
    """Result for one atomic claim after adversarial search + evidence judge."""
    claim: AtomicClaim
    verdict: EvidenceVerdict
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    judge_reasoning: Optional[str] = Field(
        default=None,
        description="LLM judge's reasoning string, for explanation grounding (Module 7).",
    )

    # [PHASE-3] entity-level cross-modal consistency fields
    entity_signal_agreement: Optional[dict] = Field(
        default=None,
        description=(
            "[PHASE-3] entity × signal agreement matrix. "
            "Keys are entity names; values are dicts of signal → agreed/disagreed/unverifiable."
        ),
    )


# ---------------------------------------------------------------------------
# Top-level Module 6 input/output — ClaimFindings
# ---------------------------------------------------------------------------

class FactCheckInput(BaseModel):
    """What callers pass to Module 6's run() entrypoint."""
    text: str = Field(description="Raw text to fact-check (caption, OCR output, or transcript).")
    source: ClaimSource = Field(
        description="Which upstream module produced this text.",
    )
    # [PHASE-3] Module 5 source metadata for entity cross-check; None in Phase 1
    reuse_source_url: Optional[str] = None
    reuse_source_published_at: Optional[str] = None
    reuse_source_location: Optional[str] = None

    # [PHASE-3] Widened-scope OCR scene text from Module 2 (street signs,
    # storefronts, banners) — folded into the adversarial search as extra
    # disambiguating context (architecture.md §Module 6, step 7).
    ocr_scene_text: Optional[str] = None


class ClaimFindings(BaseModel):
    """
<<<<<<< HEAD
    Top-level output contract for Module 6.  Frozen at end of Phase 1.

    Architecture rule (§6): this is the *entire* interface surface of Module 6.
    """
    input_text: str
    source: ClaimSource
    claims: list[AtomicClaim] = Field(description="All atomic claims extracted.")
    findings: list[SingleClaimFinding] = Field(description="Per-claim verdict + evidence.")

    # Aggregate over all claims
    overall_verdict: EvidenceVerdict = Field(
        description=(
            "Aggregate verdict: SUPPORTED if all claims supported, CONTRADICTED if any "
            "contradicted, UNCERTAIN if mixed, UNVERIFIABLE if no evidence found."
        )
    )
    overall_confidence: float = Field(ge=0.0, le=1.0)

    # [PHASE-3] drift guard
    drift_detected: Optional[bool] = Field(
        default=None,
        description=(
            "[PHASE-3] True when the recomposed claims diverge from the original text "
            "beyond the cosine-similarity threshold."
        ),
    )
    drift_score: Optional[float] = None

    # [PHASE-3] echo-chamber summary
    echo_chamber_detected: Optional[bool] = None
    unique_source_domains: Optional[int] = None

    error: Optional[str] = Field(
        default=None,
        description="Set when fact-checking could not complete. Fail honest, never silent.",
    )
=======
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
>>>>>>> d3d2c45df93abffce0459e62fed0f32a1920cf8f
