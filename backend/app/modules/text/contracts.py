"""
Module 2B — Synthetic Text Detection
Pydantic contracts (input + output). No logic lives here.

Phase 1: contract is authored and frozen so 1B can include
SyntheticTextFindings in GraphState. The actual classifier
is wired in Phase 2 (team_roadmaps.md).

Architecture §6 rule: this module takes a plain string + source tag,
returns SyntheticTextFindings, and has zero knowledge of which module
produced the text or what happens to the score afterward.
"""
from __future__ import annotations

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class TextSource(str, Enum):
    CAPTION = "caption"       # raw input caption / Module 1
    OCR = "ocr"               # Module 2 PaddleOCR
    TRANSCRIPT = "transcript" # Module 4 Whisper


class SyntheticTextVerdict(str, Enum):
    AI_LIKELY = "ai_likely"
    HUMAN_LIKELY = "human_likely"
    INCONCLUSIVE = "inconclusive"
    NOT_ASSESSED = "not_assessed"   # text too short; Guiding Principle 4


class TextInput(BaseModel):
    """What callers pass to Module 2B's run() entrypoint."""
    text: str
    source: TextSource


class SyntheticTextFindings(BaseModel):
    """
    Top-level output contract for Module 2B.  Frozen at end of Phase 1.

    Architecture note (§Module 2B):
    - score: probability the text is AI-generated [0, 1]; None when not_assessed.
    - verdict: the categorical label produced from score + length gate.
    - method: which scorer(s) produced the score
      ('classifier', 'perplexity_ratio', 'both', 'not_assessed').
    - text_length: token count of the input (aids downstream calibration).

    Guiding Principle 2 (Signals, not verdicts) applies with extra force here
    — this feeds Module 7's fusion as *one input among several*, never a
    standalone real/fake call.
    """
    source: TextSource
    text_length: int = Field(description="Approximate token count of the input text.")
    score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="AI-generated probability; None when verdict is NOT_ASSESSED.",
    )
    verdict: SyntheticTextVerdict
    method: str = Field(
        description=(
            "Which scorer produced the result: 'classifier', 'perplexity_ratio', "
            "'both', or 'not_assessed'."
        )
    )

    # Phase 4 stretch: perplexity-ratio cross-check surfaced alongside classifier
    perplexity_ratio_score: Optional[float] = Field(
        default=None,
        description="[PHASE-4] Binoculars-style perplexity-ratio score, if computed.",
    )

    error: Optional[str] = Field(
        default=None,
        description="Set when scoring could not complete. Fail honest, never silent.",
    )
