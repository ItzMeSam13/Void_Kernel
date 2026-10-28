"""
Module 6 — drift_guard.py
Essence/Claim Drift Guard (Phase 3).

Architecture reference (§Module 6, step 2):
  "[Improvement] Essence Drift Guard — cosine-similarity check (local
   sentence-transformers, no API cost) between the original
   caption/transcript and the recomposed extracted claims. Without it,
   a bad OCR read or bad Whisper transcript silently becomes the 'claim'
   that gets fact-checked, and nobody notices."

Phase 1: this file existed as a typed stub, always returning
drift_detected=False / drift_score=None, so the module's interface was
complete without blocking on the model.

Phase 3: real sentence-transformers cosine-similarity check. Consumers
(run.py) surface drift_detected/drift_score in ClaimFindings per Guiding
Principle 1 (never collapse findings) — this module does not itself
decide to abort fact-checking on drift, it only reports it honestly.
"""
from __future__ import annotations

import warnings
from functools import lru_cache
from typing import Optional

# Cosine distance (1 - similarity) above which drift is flagged.
DRIFT_THRESHOLD = 0.35

_MODEL_NAME = "all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def _get_model():
    """Lazily load the sentence-transformers model once per process."""
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(_MODEL_NAME)


def check_drift(
    original_text: str,
    recomposed_claims: list[str],
) -> tuple[bool, Optional[float]]:
    """
    Compare `original_text` to the recomposed string of extracted claims
    using sentence-transformers cosine similarity.

    Returns:
      (drift_detected: bool, drift_score: float | None)
      drift_score is the cosine *distance* (1 - similarity), 0 = identical.
      drift_score is None, drift_detected is False, when the check could
      not complete — fail open rather than block fact-checking on an
      unrelated model-loading failure (Guiding Principle 4).
    """
    if not original_text.strip() or not recomposed_claims:
        return False, None

    try:
        from sentence_transformers import util

        model = _get_model()
        recomposed = " ".join(recomposed_claims)
        emb_orig = model.encode(original_text, convert_to_tensor=True)
        emb_recomp = model.encode(recomposed, convert_to_tensor=True)
        similarity = float(util.cos_sim(emb_orig, emb_recomp)[0][0])
        distance = round(1.0 - similarity, 4)
        return distance > DRIFT_THRESHOLD, distance
    except Exception as exc:
        warnings.warn(f"[Module6/drift_guard] Drift check failed: {exc}. Failing open.")
        return False, None
