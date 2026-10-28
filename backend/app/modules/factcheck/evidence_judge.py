"""
Module 6 — evidence_judge.py
Evaluate raw search hits against an atomic claim and produce a verdict.

Phase 1 architecture (§Module 6, step 5):
  "Merge the guide's DeBERTa NLI step with Veritas's single structured
   LLM-judge call: classify each evidence item by relevance/stance/
   source-type, then render supported | contradicted | uncertain |
   unverifiable. Use DeBERTa NLI as a cheap local pre-filter (relevance/
   stance) before the one LLM call does the final judgment."

Concretely:
  1. For each raw hit, run DeBERTa NLI cross-encoder to get a
     (relevance_score, stance) pre-filter score — discard low-relevance
     hits before spending any LLM tokens.
  2. Pass the surviving evidence to a single Gemini call that returns
     structured JSON: per-item stance + a final verdict with reasoning.
  3. Return a list[EvidenceItem] + SingleClaimFinding.

Isolation: takes an AtomicClaim + list[dict] raw hits, returns structured
output. Zero knowledge of orchestration or other modules.
"""
from __future__ import annotations

import json
import os
import re
import warnings
from typing import Optional

import google.generativeai as genai

from .contracts import (
    AtomicClaim,
    EvidenceItem,
    EvidenceVerdict,
    SingleClaimFinding,
    Stance,
)
from .web_search import ECHO_CHAMBER_CONFIDENCE_MULTIPLIER, root_domain


# ---------------------------------------------------------------------------
# DeBERTa NLI pre-filter
# ---------------------------------------------------------------------------

_NLI_MODEL_NAME = "cross-encoder/nli-deberta-v3-base"
_NLI_RELEVANCE_THRESHOLD = 0.3   # discard hits below this relevance score
_nli_model = None  # lazy-loaded


def _get_nli_model():
    global _nli_model
    if _nli_model is None:
        from sentence_transformers import CrossEncoder
        _nli_model = CrossEncoder(_NLI_MODEL_NAME)
    return _nli_model


def _nli_prefilter(
    claim_text: str,
    hits: list[dict],
) -> list[tuple[dict, float, Stance]]:
    """
    Score each hit's snippet against the claim using DeBERTa NLI.
    Returns list of (hit, relevance_score, stance) for hits that pass
    the relevance threshold.

    DeBERTa cross-encoder output labels: ["contradiction", "entailment", "neutral"]
    """
    if not hits:
        return []

    try:
        model = _get_nli_model()
        snippets = [h.get("snippet") or h.get("content", "") for h in hits]
        pairs = [(claim_text, s) for s in snippets]
        scores = model.predict(pairs, apply_softmax=True)
        # scores shape: (N, 3) — [contradiction, entailment, neutral]

        results = []
        for hit, score_row in zip(hits, scores):
            contradiction_p, entailment_p, neutral_p = float(score_row[0]), float(score_row[1]), float(score_row[2])
            relevance = max(entailment_p, contradiction_p)  # neutral is not relevant
            if relevance < _NLI_RELEVANCE_THRESHOLD:
                continue
            if entailment_p >= contradiction_p:
                stance = Stance.SUPPORTS
            else:
                stance = Stance.CONTRADICTS
            results.append((hit, relevance, stance))

        return results

    except Exception as exc:
        warnings.warn(f"[Module6/evidence_judge] NLI pre-filter failed: {exc}. Skipping filter.")
        # Fail open: pass all hits through without NLI scoring
        return [(h, 0.5, Stance.NEUTRAL) for h in hits]


# ---------------------------------------------------------------------------
# Gemini evidence judge
# ---------------------------------------------------------------------------

_JUDGE_SYSTEM = """You are a rigorous fact-checking assistant.
You will be given an atomic claim and a set of evidence snippets.

For each evidence item output a JSON object with:
  "source_url"   : the URL of the source (copy from input exactly)
  "stance"       : one of "supports" | "contradicts" | "neutral" | "irrelevant"
  "relevance"    : float 0.0–1.0

Then output an overall verdict object:
  "verdict"      : one of "supported" | "contradicted" | "uncertain" | "unverifiable"
  "confidence"   : float 0.0–1.0
  "reasoning"    : 1–3 sentence explanation citing specific evidence

Return ONLY valid JSON in this exact shape:
{
  "evidence": [...],
  "verdict": "...",
  "confidence": 0.0,
  "reasoning": "..."
}"""

_JUDGE_USER = """Claim: {claim}

Evidence:
{evidence_block}"""


def _configure_genai() -> None:
    api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise EnvironmentError("GOOGLE_API_KEY or GEMINI_API_KEY not set.")
    genai.configure(api_key=api_key)


def _build_evidence_block(filtered: list[tuple[dict, float, Stance]]) -> str:
    lines = []
    for i, (hit, _, _) in enumerate(filtered, 1):
        url = hit.get("url") or hit.get("source_url", "unknown")
        title = hit.get("title", "")
        snippet = hit.get("snippet") or hit.get("content", "")[:500]
        source_type = hit.get("_source_type", "web")
        lines.append(f"[{i}] ({source_type}) {title}\nURL: {url}\n{snippet}\n")
    return "\n".join(lines)


def _parse_judge_response(raw: str) -> dict:
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    return json.loads(cleaned)


def _map_verdict(raw: str) -> EvidenceVerdict:
    mapping = {
        "supported": EvidenceVerdict.SUPPORTED,
        "contradicted": EvidenceVerdict.CONTRADICTED,
        "uncertain": EvidenceVerdict.UNCERTAIN,
        "unverifiable": EvidenceVerdict.UNVERIFIABLE,
    }
    return mapping.get(raw.lower(), EvidenceVerdict.UNCERTAIN)


def _map_stance(raw: str) -> Stance:
    mapping = {
        "supports": Stance.SUPPORTS,
        "contradicts": Stance.CONTRADICTS,
        "neutral": Stance.NEUTRAL,
        "irrelevant": Stance.IRRELEVANT,
    }
    return mapping.get(raw.lower(), Stance.NEUTRAL)


# ---------------------------------------------------------------------------
# Public function
# ---------------------------------------------------------------------------

def judge_claim(
    claim: AtomicClaim,
    raw_hits: list[dict],
    extra_context: Optional[str] = None,
    echo_chamber_flagged: bool = False,
    dominant_domains: Optional[set[str]] = None,
) -> SingleClaimFinding:
    """
    Evaluate `raw_hits` against `claim` and return a SingleClaimFinding.

    Steps:
      1. NLI pre-filter to discard irrelevant hits.
      2. Single Gemini call over surviving evidence.
      3. Map LLM JSON → EvidenceItem list + SingleClaimFinding.

    [PHASE-3] `echo_chamber_flagged`/`dominant_domains` come from
    web_search.detect_echo_chamber() over this claim's combined hits
    (architecture.md §Module 6, step 4): EvidenceItems whose domain is
    "dominant" are tagged, and confidence is scaled by
    ECHO_CHAMBER_CONFIDENCE_MULTIPLIER when the claim's evidence set as a
    whole is flagged.

    Falls back to UNVERIFIABLE with an error note if all steps fail.
    """
    dominant_domains = dominant_domains or set()
    if not raw_hits:
        return SingleClaimFinding(
            claim=claim,
            verdict=EvidenceVerdict.UNVERIFIABLE,
            confidence=0.0,
            evidence=[],
            judge_reasoning="No evidence retrieved.",
        )

    # Step 1: NLI pre-filter
    filtered = _nli_prefilter(claim.text, raw_hits)
    if not filtered:
        return SingleClaimFinding(
            claim=claim,
            verdict=EvidenceVerdict.UNVERIFIABLE,
            confidence=0.0,
            evidence=[],
            judge_reasoning="All retrieved evidence was below relevance threshold.",
        )

    # Step 2: Gemini judge
    try:
        _configure_genai()
        model = genai.GenerativeModel(
            model_name=os.environ.get("GEMINI_MODEL", "gemini-2.0-flash"),
            system_instruction=_JUDGE_SYSTEM,
        )
        evidence_block = _build_evidence_block(filtered)
        prompt = _JUDGE_USER.format(claim=claim.text, evidence_block=evidence_block)
        response = model.generate_content(prompt)
        parsed = _parse_judge_response(response.text)

        # Build EvidenceItem list
        ev_items: list[EvidenceItem] = []
        raw_ev_list = parsed.get("evidence", [])
        # Map back to original hits via position
        for i, raw_ev in enumerate(raw_ev_list):
            if i >= len(filtered):
                break
            orig_hit, nli_relevance, nli_stance = filtered[i]
            url = raw_ev.get("source_url") or orig_hit.get("url", "")
            ev_items.append(
                EvidenceItem(
                    source_url=url,
                    source_title=orig_hit.get("title"),
                    snippet=orig_hit.get("snippet") or orig_hit.get("content", "")[:500],
                    stance=_map_stance(raw_ev.get("stance", "neutral")),
                    relevance_score=float(raw_ev.get("relevance", nli_relevance)),
                    source_type=orig_hit.get("_source_type", "web"),
                    echo_chamber_flagged=root_domain(orig_hit) in dominant_domains,
                )
            )

        verdict = _map_verdict(parsed.get("verdict", "uncertain"))
        confidence = float(parsed.get("confidence", 0.5))
        if echo_chamber_flagged:
            confidence = round(confidence * ECHO_CHAMBER_CONFIDENCE_MULTIPLIER, 4)
        reasoning = parsed.get("reasoning", "")

        return SingleClaimFinding(
            claim=claim,
            verdict=verdict,
            confidence=confidence,
            evidence=ev_items,
            judge_reasoning=reasoning,
        )

    except Exception as exc:
        warnings.warn(f"[Module6/evidence_judge] Gemini judge failed: {exc}")
        # Graceful fallback using NLI pre-filter stances only
        ev_items = [
            EvidenceItem(
                source_url=hit.get("url") or hit.get("source_url", ""),
                source_title=hit.get("title"),
                snippet=(hit.get("snippet") or hit.get("content", ""))[:500],
                stance=stance,
                relevance_score=relevance,
                source_type=hit.get("_source_type", "web"),
                echo_chamber_flagged=root_domain(hit) in dominant_domains,
            )
            for hit, relevance, stance in filtered
        ]
        support_count = sum(1 for e in ev_items if e.stance == Stance.SUPPORTS)
        contra_count = sum(1 for e in ev_items if e.stance == Stance.CONTRADICTS)
        if contra_count > support_count:
            verdict = EvidenceVerdict.CONTRADICTED
        elif support_count > 0:
            verdict = EvidenceVerdict.UNCERTAIN
        else:
            verdict = EvidenceVerdict.UNVERIFIABLE

        fallback_confidence = 0.4
        if echo_chamber_flagged:
            fallback_confidence = round(fallback_confidence * ECHO_CHAMBER_CONFIDENCE_MULTIPLIER, 4)

        return SingleClaimFinding(
            claim=claim,
            verdict=verdict,
            confidence=fallback_confidence,
            evidence=ev_items,
            judge_reasoning=f"LLM judge unavailable ({exc}); verdict from NLI pre-filter only.",
        )
