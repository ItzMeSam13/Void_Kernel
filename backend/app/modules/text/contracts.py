"""
modules/text/contracts.py — Module 2B public contracts (Person 1 owns this).

TextInput / SyntheticTextFindings form the ONLY interface surface of Module 2B.
architecture.md §Module 2B:
  "SyntheticTextFindings { score, verdict, method, source, text_length }"
"""
from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field


TextSource = Literal["caption", "ocr", "transcript"]
TextVerdict = Literal["ai_likely", "human_likely", "inconclusive", "not_assessed"]


class TextInput(BaseModel):
    """Input to Module 2B's detect_synthetic_text() entrypoint."""
    text:   str           = Field(..., description="Plain text to score.")
    source: TextSource    = Field(..., description="Which module produced this text.")


class SyntheticTextFindings(BaseModel):
    """
    Output of Module 2B's detect_synthetic_text() entrypoint.
    Matches the stub in orchestrator/state.py — keep in sync.
    """
    score:       Optional[float]   = Field(None, ge=0.0, le=1.0,
        description="Probability text is AI-generated (0=human, 1=AI).")
    verdict:     TextVerdict       = "not_assessed"
    method:      Optional[str]     = Field(None,
        description="Classifier name used (e.g. 'roberta-base-openai-detector').")
    source:      Optional[str]     = Field(None,
        description="caption | ocr | transcript — which text was scored.")
    text_length: Optional[int]     = None
    error:       Optional[str]     = None
