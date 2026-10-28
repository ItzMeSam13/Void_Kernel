"""
<<<<<<< HEAD
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
=======
modules/text/synthetic_text.py — AI-text classifier (Module 2B core).

Primary scorer: Hello-SimpleAI/chatgpt-detector-roberta
  - Fine-tuned RoBERTa-base binary classifier (human vs. AI-generated text).
  - Apache-2.0 licence, runs fully locally via HuggingFace Transformers.

Length gate (architecture.md §Module 2B):
  Below MIN_TOKEN_COUNT tokens → not_assessed.
  AI-text detectors have well-documented false-positive rates on short text;
  never let a 5-word caption produce a misleading "87% AI-generated" number.

Model loading is lazy and cached — the process pays the startup cost only
once per worker, regardless of how many jobs run.

Guiding Principle 2 applies with extra force here: this score is a SIGNAL
fed into Module 7's consistency axis, never a standalone verdict.
"""
from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

MIN_TOKEN_COUNT  = 50          # architecture.md §Module 2B
MODEL_NAME       = "Hello-SimpleAI/chatgpt-detector-roberta"
MAX_INPUT_TOKENS = 512         # model's context window; truncate gracefully

# Label map — verify against the model card on first deploy
_AI_LABELS    = {"ChatGPT", "fake", "generated", "AI", "machine"}
_HUMAN_LABELS = {"Human", "real", "human"}


# ── Lazy model singleton ──────────────────────────────────────────────────────

_pipeline = None
_tokenizer = None


def _load_model():
    """
    Load the classifier pipeline once per process.
    Falls back gracefully if transformers is not installed or the model
    cannot be fetched (no internet, no cache).
    """
    global _pipeline
    if _pipeline is not None:
        return _pipeline

    try:
        from transformers import pipeline as hf_pipeline
        logger.info("Loading AI-text classifier %s …", MODEL_NAME)
        _pipeline = hf_pipeline(
            "text-classification",
            model=MODEL_NAME,
            truncation=True,
            max_length=MAX_INPUT_TOKENS,
            device=-1,          # CPU; set device=0 for GPU if available
        )
        logger.info("AI-text classifier loaded.")
        return _pipeline
    except Exception as exc:    # noqa: BLE001
        logger.warning("Could not load AI-text classifier: %s", exc)
        return None


# ── Public scorer ─────────────────────────────────────────────────────────────

def score_text(text: str) -> tuple[Optional[float], str, str]:
    """
    Score *text* for AI generation probability.

    Returns:
      (score, verdict, method)

      score   — float in [0, 1] = P(AI-generated), or None on failure
      verdict — "ai_likely" | "human_likely" | "inconclusive" | "not_assessed"
      method  — model name or "unavailable"
    """
    tokens = text.split()
    n_tokens = len(tokens)

    # ── Length gate ───────────────────────────────────────────────────────────
    if n_tokens < MIN_TOKEN_COUNT:
        return None, "not_assessed", "length_gate"

    # ── Load model ────────────────────────────────────────────────────────────
    clf = _load_model()
    if clf is None:
        return None, "not_assessed", "unavailable"

    # ── Inference ─────────────────────────────────────────────────────────────
    try:
        # HuggingFace pipeline returns a list of {label, score}
        result = clf(text[:MAX_INPUT_TOKENS * 6], truncation=True)   # ~6 chars/token
        if not result:
            return None, "not_assessed", "unavailable"

        top = result[0]
        label: str = top["label"]
        raw_score: float = float(top["score"])

        # Map label → AI probability score
        ai_prob = _label_to_ai_prob(label, raw_score)

        # Map score → verdict
        verdict = _verdict(ai_prob)
        return ai_prob, verdict, MODEL_NAME

    except Exception as exc:    # noqa: BLE001
        logger.debug("score_text inference error: %s", exc)
        return None, "not_assessed", "error"


def _label_to_ai_prob(label: str, score: float) -> float:
    """
    Normalise the model's label+score to a P(AI-generated) float.

    The model may output "ChatGPT"/"Human" or "fake"/"real" depending on
    the checkpoint version.  We handle both conventions.
    """
    # If the label points to AI/fake → score IS the AI probability
    if any(lbl.lower() in label.lower() for lbl in _AI_LABELS):
        return score
    # If the label points to human/real → complement
    if any(lbl.lower() in label.lower() for lbl in _HUMAN_LABELS):
        return 1.0 - score
    # Unknown label: treat as uncertain
    logger.debug("Unknown label %r from AI-text classifier — treating as 0.5", label)
    return 0.5


def _verdict(ai_prob: float) -> str:
    """
    Map P(AI-generated) to a verdict string.

    Thresholds are intentionally conservative (architecture.md §Module 2B
    Guiding Principle 2):
      > 0.80 → ai_likely
      < 0.30 → human_likely
      else   → inconclusive
    """
    if ai_prob > 0.80:
        return "ai_likely"
    if ai_prob < 0.30:
        return "human_likely"
    return "inconclusive"
>>>>>>> d3d2c45df93abffce0459e62fed0f32a1920cf8f
