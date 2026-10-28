"""
Module 6 — web_search.py
Adversarial Tavily search: two queries per claim (confirming + contradicting),
run concurrently via asyncio.gather.

Architecture reference (§Module 6, step 3):
  - "Two Tavily queries per claim (confirming + contradicting), run
    concurrently via asyncio.gather, same as Veritas."
  - Ported from Veritas's services/web_search.py — query-builder and
    dual-search pattern reused; fact-checking content re-targeted.

Phase 1 scope: adversarial search only.
  Phase 3 adds: echo-chamber detection (flag when ≥3 results share a root
  domain or <3 unique domains appear total; 0.75× confidence multiplier).

Isolation: takes a plain string (claim text), returns list[dict] raw hits.
The evidence_judge.py layer converts these to EvidenceItem objects.
"""
from __future__ import annotations

import asyncio
import os
from typing import Optional

from tavily import TavilyClient, AsyncTavilyClient


# ---------------------------------------------------------------------------
# Query builder — adversarial pair
# ---------------------------------------------------------------------------

def _build_confirming_query(claim: str) -> str:
    """Build a query biased toward finding supporting evidence."""
    return f'evidence supporting: "{claim}"'


def _build_contradicting_query(claim: str) -> str:
    """Build a query biased toward finding refuting evidence."""
    return f'evidence contradicting or debunking: "{claim}"'


# ---------------------------------------------------------------------------
# Async search (primary path)
# ---------------------------------------------------------------------------

async def _search_async(
    client: AsyncTavilyClient,
    query: str,
    source_type_tag: str,
    max_results: int,
) -> list[dict]:
    """Run one Tavily search and tag each result with source_type_tag."""
    try:
        response = await client.search(
            query=query,
            max_results=max_results,
            include_answer=False,
            include_raw_content=False,
        )
        hits = response.get("results", [])
        for hit in hits:
            hit["_source_type"] = source_type_tag
        return hits
    except Exception as exc:
        import warnings
        warnings.warn(f"[Module6/web_search] Tavily query failed ({source_type_tag}): {exc}")
        return []


async def adversarial_search_async(
    claim_text: str,
    max_results_per_query: int = 5,
    extra_context: Optional[str] = None,
) -> list[dict]:
    """
    Run confirming + contradicting Tavily searches concurrently.

    `extra_context` (Phase 3): widened OCR scene-text from Module 2 folded
    in as disambiguating context (architecture.md §Module 6, step 7).

    Returns a flat list of raw Tavily hit dicts, each tagged with
    '_source_type' ∈ {'tavily_confirming', 'tavily_contradicting'}.
    """
    api_key = os.environ.get("TAVILY_API_KEY", "")
    if not api_key:
        import warnings
        warnings.warn("[Module6/web_search] TAVILY_API_KEY not set; returning empty results.")
        return []

    base_claim = claim_text
    if extra_context:
        base_claim = f"{claim_text} [context: {extra_context}]"

    confirming_q = _build_confirming_query(base_claim)
    contradicting_q = _build_contradicting_query(base_claim)

    async with AsyncTavilyClient(api_key=api_key) as client:
        confirming_hits, contradicting_hits = await asyncio.gather(
            _search_async(client, confirming_q, "tavily_confirming", max_results_per_query),
            _search_async(client, contradicting_q, "tavily_contradicting", max_results_per_query),
        )

    return confirming_hits + contradicting_hits


# ---------------------------------------------------------------------------
# Sync wrapper (for callers that can't use async)
# ---------------------------------------------------------------------------

def adversarial_search(
    claim_text: str,
    max_results_per_query: int = 5,
    extra_context: Optional[str] = None,
) -> list[dict]:
    """
    Synchronous wrapper around adversarial_search_async.
    Uses asyncio.run() — do NOT call from inside an already-running
    event loop (use adversarial_search_async directly instead).
    """
    return asyncio.run(
        adversarial_search_async(claim_text, max_results_per_query, extra_context)
    )


# ---------------------------------------------------------------------------
# Google Fact Check Tools API (supplementary, Phase 1)
# ---------------------------------------------------------------------------

def google_fact_check_search(claim_text: str, max_results: int = 5) -> list[dict]:
    """
    Query the Google Fact Check Tools API for matching fact-check articles.

    Returns raw API hits tagged with '_source_type': 'google_fact_check'.
    Returns [] on missing API key or any error (fail honest).

    API reference:
      https://developers.google.com/fact-check/tools/api/reference/rest/v1alpha1/claims/search
    """
    api_key = os.environ.get("GOOGLE_FACT_CHECK_API_KEY", "")
    if not api_key:
        return []

    import requests
    try:
        resp = requests.get(
            "https://factchecktools.googleapis.com/v1alpha1/claims:search",
            params={"query": claim_text, "pageSize": max_results, "key": api_key},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        hits = data.get("claims", [])
        for hit in hits:
            hit["_source_type"] = "google_fact_check"
        return hits
    except Exception as exc:
        import warnings
        warnings.warn(f"[Module6/web_search] Google Fact Check API failed: {exc}")
        return []
