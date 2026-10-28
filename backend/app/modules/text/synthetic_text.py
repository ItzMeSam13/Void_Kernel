"""
Module 2B — synthetic_text.py
Primary AI-generated-text classifier + token-count helper.

Phase 2 (team_roadmaps.md): wires in the primary classifier. The length
gate itself lives in run.py (so it can short-circuit before the model is
even loaded); this file only owns the token count and the classifier call.

Phase 4 stretch (not built here): perplexity-ratio cross-check. contracts.py
already reserves `perplexity_ratio_score` for it.
"""
from __future__ import annotations

import warnings
from functools import lru_cache
from typing import Optional

from .contracts import SyntheticTextVerdict

# Below this many whitespace-tokens, AI-text classifiers are unreliable
# (architecture.md Module 2B design note; Guiding Principle 4).
MIN_TOKEN_COUNT = 20

# Pretrained RoBERTa-based open-source AI-text detector (architecture.md
# Module 2B: "a pretrained AI-text classifier ... run locally, no per-call
# API cost"). Labels are "Real" / "Fake", where "Fake" = AI-generated.
CLASSIFIER_MODEL_NAME = "openai-community/roberta-base-openai-detector"

AI_LIKELY_THRESHOLD = 0.65
HUMAN_LIKELY_THRESHOLD = 0.35


def count_tokens(text: str) -> int:
    """
    Approximate token count via whitespace split.

    Deliberately model-independent (no tokenizer load) so the length gate
    in run.py works even when the classifier itself fails to load.
    """
    return len(text.split())


@lru_cache(maxsize=1)
def _get_classifier():
    """Lazily load the HF pipeline once per process."""
    from transformers import pipeline

    return pipeline("text-classification", model=CLASSIFIER_MODEL_NAME)


def _verdict_from_score(ai_score: float) -> SyntheticTextVerdict:
    if ai_score >= AI_LIKELY_THRESHOLD:
        return SyntheticTextVerdict.AI_LIKELY
    if ai_score <= HUMAN_LIKELY_THRESHOLD:
        return SyntheticTextVerdict.HUMAN_LIKELY
    return SyntheticTextVerdict.INCONCLUSIVE


def classify(text: str) -> tuple[Optional[float], SyntheticTextVerdict, Optional[str]]:
    """
    Runs the primary AI-text classifier on `text`.

    Returns (ai_score, verdict, error):
      - ai_score: probability the text is AI-generated, in [0, 1]; None on error.
      - verdict: NOT_ASSESSED when ai_score is None, else AI_LIKELY/HUMAN_LIKELY/INCONCLUSIVE.
      - error: human-readable message, or None on success.

    Never raises — Guiding Principle 4 (fail honest, never silent).
    """
    try:
        clf = _get_classifier()
        result = clf(text, truncation=True)[0]
    except Exception as exc:
        warnings.warn(f"[Module2B/synthetic_text] Classifier failed: {exc}")
        return None, SyntheticTextVerdict.NOT_ASSESSED, f"Classifier failed: {exc}"

    label = result["label"].lower()
    raw_score = float(result["score"])

    if "fake" in label:
        ai_score = raw_score
    elif "real" in label:
        ai_score = 1.0 - raw_score
    else:
        warnings.warn(f"[Module2B/synthetic_text] Unrecognized classifier label '{result['label']}'")
        return None, SyntheticTextVerdict.NOT_ASSESSED, f"Unrecognized classifier label: {result['label']}"

    return round(ai_score, 4), _verdict_from_score(ai_score), None
