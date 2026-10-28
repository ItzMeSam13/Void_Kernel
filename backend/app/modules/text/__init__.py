"""
modules/text/__init__.py — Module 2B: Synthetic Text Detection.

Public entrypoint: run(TextInput) → SyntheticTextFindings

Implementation (architecture.md §Module 2B):
  1. Length gate → not_assessed when text is below MIN_TOKEN_COUNT.
  2. Primary: Hello-SimpleAI/chatgpt-detector-roberta (RoBERTa binary classifier).
  3. Returns SyntheticTextFindings with score, verdict, method, source, text_length.

Signal, not verdict (Guiding Principle 2):
  This score feeds Module 7's consistency axis as one input among several.
  It is NEVER a standalone fake/real determination.

Isolation rule (architecture.md §6):
  This module takes a plain string + source tag, returns SyntheticTextFindings,
  and has zero knowledge of which module produced the text or what happens
  to the score afterward.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

from app.modules.text.contracts import TextInput, SyntheticTextFindings
from app.modules.text.synthetic_text import score_text, MIN_TOKEN_COUNT

logger = logging.getLogger(__name__)


async def run(inp: TextInput) -> SyntheticTextFindings:
    """
    Module 2B entrypoint.

    Runs the AI-text classifier in a thread pool so it does not block the
    async event loop (Transformers inference is CPU-bound / synchronous).
    """
    text   = inp.text.strip()
    tokens = text.split()
    n_tok  = len(tokens)

    # ── Length gate ───────────────────────────────────────────────────────────
    if n_tok < MIN_TOKEN_COUNT:
        logger.debug(
            "Module 2B: length gate fired (%d tokens < %d) — not_assessed",
            n_tok, MIN_TOKEN_COUNT,
        )
        return SyntheticTextFindings(
            verdict="not_assessed",
            source=inp.source,
            text_length=n_tok,
        )

    # ── Inference (thread pool — keeps event loop unblocked) ─────────────────
    try:
        loop = asyncio.get_event_loop()
        score, verdict, method = await loop.run_in_executor(
            None,           # default ThreadPoolExecutor
            score_text,
            text,
        )
    except Exception as exc:    # noqa: BLE001
        logger.exception("Module 2B inference error: %s", exc)
        return SyntheticTextFindings(
            verdict="not_assessed",
            source=inp.source,
            text_length=n_tok,
            error=str(exc),
        )

    logger.debug(
        "Module 2B: source=%s n_tokens=%d score=%.3f verdict=%s method=%s",
        inp.source, n_tok, score or 0.0, verdict, method,
    )

    return SyntheticTextFindings(
        score=score,
        verdict=verdict,       # type: ignore[arg-type]
        method=method,
        source=inp.source,
        text_length=n_tok,
    )
