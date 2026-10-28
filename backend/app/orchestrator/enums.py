"""
orchestrator/enums.py — Shared enums used across all modules.

Extracted from state.py to break circular imports:
  modules/*/contracts.py  →  imports Verdict, ConfidenceLevel from here
  orchestrator/state.py   →  imports findings models from modules/*/contracts.py
                          →  imports enums from here

No module or orchestrator file should define these enums locally.
"""
from __future__ import annotations

from enum import Enum


class InputModality(str, Enum):
    """What kind of media was submitted."""
    TEXT_IMAGE = "text_image"
    VIDEO      = "video"
    AUDIO_ONLY = "audio_only"


class Verdict(str, Enum):
    """
    Generic per-axis verdict.  Keeps the four axes comparable without
    collapsing them into one.
    """
    SUPPORTED          = "supported"
    CONTRADICTED       = "contradicted"
    UNCERTAIN          = "uncertain"
    UNVERIFIABLE       = "unverifiable"
    # authenticity / manipulation-specific
    LIKELY_AUTHENTIC   = "likely_authentic"
    LIKELY_MANIPULATED = "likely_manipulated"
    LIKELY_AI_GENERATED = "likely_ai_generated"
    # shared
    INCONCLUSIVE       = "inconclusive"
    NOT_ASSESSED       = "not_assessed"


class ConfidenceLevel(str, Enum):
    HIGH   = "high"
    MEDIUM = "medium"
    LOW    = "low"
    NONE   = "none"
