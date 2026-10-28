"""
Module 6 — run.py
Single public entrypoint: run(input: FactCheckInput) -> ClaimFindings

Architecture §6 rule:
  - This is the *entire* interface surface of Module 6.
  - No other module imports anything else from this package.
  - Callable standalone with zero orchestration framework installed.

Phase 1 flow:
  1. Split text into atomic claims (claim_splitter.py).
  2. [PHASE-3 placeholder] Drift guard check (drift_guard.py).
  3. For each claim, run adversarial Tavily + Google Fact Check search
     concurrently across claims (asyncio.gather over all claims).
  4. For each claim, judge evidence (evidence_judge.py).
  5. Compute aggregate verdict + confidence.
  6. Return ClaimFindings.

Phase 1 skips: drift guard (always passes), echo-chamber detection,
NER entity-tagging, entity × signal agreement matrix.

Guiding Principle 4 (fail honest): any unhandled exception returns a
ClaimFindings with error set and overall_verdict=UNVERIFIABLE.
"""
from __future__ import annotations

import asyncio
import warnings
from typing import Optional

from .claim_splitter import split_claims
from .contracts import (
    ClaimFindings,
    ClaimSource,
    EvidenceVerdict,
    FactCheckInput,
)
from .drift_guard import check_drift
from .evidence_judge import judge_claim
from .web_search import adversarial_search_async, google_fact_check_search


# ---------------------------------------------------------------------------
# Aggregate verdict helpers
# ---------------------------------------------------------------------------

def _aggregate_verdict(verdicts: list[EvidenceVerdict]) -> tuple[EvidenceVerdict, float]:
    """
    Simple aggregation across all atomic-claim verdicts:
      - Any CONTRADICTED  → CONTRADICTED (confidence = proportion contradicted)
      - All SUPPORTED     → SUPPORTED
      - All UNVERIFIABLE  → UNVERIFIABLE
      - Mixed             → UNCERTAIN
    Returns (aggregate_verdict, confidence).
    """
    if not verdicts:
        return EvidenceVerdict.UNVERIFIABLE, 0.0

    counts = {v: verdicts.count(v) for v in EvidenceVerdict}
    total = len(verdicts)

    if counts[EvidenceVerdict.CONTRADICTED] > 0:
        return EvidenceVerdict.CONTRADICTED, counts[EvidenceVerdict.CONTRADICTED] / total
    if counts[EvidenceVerdict.SUPPORTED] == total:
        return EvidenceVerdict.SUPPORTED, 1.0
    if counts[EvidenceVerdict.UNVERIFIABLE] == total:
        return EvidenceVerdict.UNVERIFIABLE, 0.0
    return EvidenceVerdict.UNCERTAIN, counts[EvidenceVerdict.UNCERTAIN] / total


# ---------------------------------------------------------------------------
# Async inner pipeline
# ---------------------------------------------------------------------------

async def _run_async(
    inp: FactCheckInput,
    extra_context: Optional[str] = None,
) -> ClaimFindings:
    """
    Async implementation — allows concurrent per-claim searches via
    asyncio.gather (Veritas's Send fan-out pattern, applied here inside
    Module 6; the top-level orchestrator doesn't need to know).
    """
    # Step 1: claim splitting
    try:
        claims = split_claims(inp.text)
    except Exception as exc:
        return ClaimFindings(
            input_text=inp.text,
            source=inp.source,
            claims=[],
            findings=[],
            overall_verdict=EvidenceVerdict.UNVERIFIABLE,
            overall_confidence=0.0,
            error=f"Claim splitting failed: {exc}",
        )

    if not claims:
        return ClaimFindings(
            input_text=inp.text,
            source=inp.source,
            claims=[],
            findings=[],
            overall_verdict=EvidenceVerdict.UNVERIFIABLE,
            overall_confidence=0.0,
            error="No claims could be extracted from the input text.",
        )

    # Step 2: drift guard (Phase 3 — always passes in Phase 1)
    recomposed = [c.text for c in claims]
    drift_detected, drift_score = check_drift(inp.text, recomposed)
    # If drift is detected (Phase 3+), we could flag and return early.
    # In Phase 1 drift_detected is always False, so this is a no-op.

    # Step 3: concurrent adversarial search across all claims
    search_tasks = [
        adversarial_search_async(claim.text, extra_context=extra_context)
        for claim in claims
    ]
    # Also run Google Fact Check in parallel (sync calls wrapped)
    gfc_hits_per_claim = [
        google_fact_check_search(claim.text) for claim in claims
    ]
    search_results = await asyncio.gather(*search_tasks, return_exceptions=True)

    # Step 4: judge each claim
    findings = []
    for claim, raw_search, gfc_hits in zip(claims, search_results, gfc_hits_per_claim):
        if isinstance(raw_search, Exception):
            warnings.warn(f"[Module6/run] Search failed for claim '{claim.claim_id}': {raw_search}")
            raw_search = []
        combined_hits = list(raw_search) + list(gfc_hits)
        finding = judge_claim(claim, combined_hits)
        findings.append(finding)

    # Step 5: aggregate
    verdicts = [f.verdict for f in findings]
    confidences = [f.confidence for f in findings]
    overall_verdict, overall_conf = _aggregate_verdict(verdicts)
    # Weight aggregate confidence by mean of per-claim confidences
    mean_conf = sum(confidences) / len(confidences) if confidences else 0.0
    final_confidence = (overall_conf + mean_conf) / 2

    return ClaimFindings(
        input_text=inp.text,
        source=inp.source,
        claims=claims,
        findings=findings,
        overall_verdict=overall_verdict,
        overall_confidence=round(final_confidence, 4),
        drift_detected=drift_detected,
        drift_score=drift_score,
    )


# ---------------------------------------------------------------------------
# Public entrypoint
# ---------------------------------------------------------------------------

def run(inp: FactCheckInput) -> ClaimFindings:
    """
    Module 6 entrypoint.

    Accepts a FactCheckInput (text + source tag).
    Returns ClaimFindings.  Never raises — errors are surfaced in
    ClaimFindings.error per Guiding Principle 4.

    Uses asyncio.run() internally — do NOT call from inside an already-
    running event loop.  If you need async, call _run_async() directly.
    """
    try:
        return asyncio.run(_run_async(inp))
    except Exception as exc:
        return ClaimFindings(
            input_text=inp.text,
            source=inp.source,
            claims=[],
            findings=[],
            overall_verdict=EvidenceVerdict.UNVERIFIABLE,
            overall_confidence=0.0,
            error=f"Unhandled error in Module 6: {exc}",
        )
