"""
Module 2B — run.py
Single public entrypoint: run(input: TextInput) -> SyntheticTextFindings

Architecture §6 rule:
  - This is the *entire* interface surface of Module 2B.
  - No other module imports anything else from this package.
  - Callable identically regardless of whether the text came from Module 1's
    caption, Module 2's OCR, or Module 4's transcript — the caller only sets
    TextInput.source.

Phase 2 flow (team_roadmaps.md):
  1. Length gate — below MIN_TOKEN_COUNT whitespace-tokens, return
     NOT_ASSESSED without invoking the classifier (Guiding Principle 4:
     fail honest rather than produce a misleading score on short text).
  2. Run the primary classifier (synthetic_text.classify).
  3. Return SyntheticTextFindings.

Phase 4 stretch (not built here): perplexity-ratio cross-check, surfaced
alongside the classifier score rather than replacing it — contracts.py
already reserves `perplexity_ratio_score` for this.
"""
from __future__ import annotations

from .contracts import SyntheticTextFindings, SyntheticTextVerdict, TextInput
from .synthetic_text import MIN_TOKEN_COUNT, classify, count_tokens


def run(inp: TextInput) -> SyntheticTextFindings:
    """
    Module 2B entrypoint.

    Accepts a TextInput (text + source tag). Returns SyntheticTextFindings.
    Never raises — errors are surfaced in SyntheticTextFindings.error per
    Guiding Principle 4.
    """
    try:
        text_length = count_tokens(inp.text)

        if text_length < MIN_TOKEN_COUNT:
            return SyntheticTextFindings(
                source=inp.source,
                text_length=text_length,
                score=None,
                verdict=SyntheticTextVerdict.NOT_ASSESSED,
                method="not_assessed",
            )

        score, verdict, error = classify(inp.text)

        return SyntheticTextFindings(
            source=inp.source,
            text_length=text_length,
            score=score,
            verdict=verdict,
            method="not_assessed" if error else "classifier",
            error=error,
        )
    except Exception as exc:
        return SyntheticTextFindings(
            source=inp.source,
            text_length=count_tokens(inp.text) if inp.text else 0,
            score=None,
            verdict=SyntheticTextVerdict.NOT_ASSESSED,
            method="not_assessed",
            error=f"Unhandled error in Module 2B: {exc}",
        )
