"""
Module 6 — drift_guard.py
Essence/Claim Drift Guard (Phase 3 — stub in Phase 1).

Architecture reference (§Module 6, step 2):
  "[Improvement] Essence Drift Guard — cosine-similarity check (local
   sentence-transformers, no API cost) between the original
   caption/transcript and the recomposed extracted claims. Without it,
   a bad OCR read or bad Whisper transcript silently becomes the 'claim'
   that gets fact-checked, and nobody notices."

Phase 1: this file exists as a typed stub so the module's interface is
complete. The guard always returns drift_detected=False and drift_score=None
in Phase 1. Phase 3 will fill in the real implementation.

Consumers (run.py) check drift_detected before proceeding; the stub
simply never blocks — safe default for Phase 1.
"""
from __future__ import annotations

from typing import Optional


# Phase 3 threshold — cosine distance above which drift is flagged
DRIFT_THRESHOLD = 0.35


def check_drift(
    original_text: str,
    recomposed_claims: list[str],
) -> tuple[bool, Optional[float]]:
    """
    Compare `original_text` to the recomposed string of extracted claims
    using sentence-transformers cosine similarity.

    Phase 1: always returns (False, None) — drift guard is a Phase 3 feature.
    Phase 3: replace the body below with the real sentence-transformers call.

    Returns:
      (drift_detected: bool, drift_score: float | None)
      drift_score is the cosine *distance* (1 - similarity), 0 = identical.
    """
    # [PHASE-3] Implementation placeholder
    # from sentence_transformers import SentenceTransformer, util
    # model = SentenceTransformer("all-MiniLM-L6-v2")
    # recomposed = " ".join(recomposed_claims)
    # emb_orig = model.encode(original_text, convert_to_tensor=True)
    # emb_recomp = model.encode(recomposed, convert_to_tensor=True)
    # similarity = float(util.cos_sim(emb_orig, emb_recomp)[0][0])
    # distance = 1.0 - similarity
    # return distance > DRIFT_THRESHOLD, distance
    return False, None
