"""
Module 2 — Image Intelligence: canonical entrypoint (architecture.md §6).

Exposes the standard module interface:
    run(input: ImageInput) -> ImageFindings

Also re-exports the direct public adapter required by Person 2's video module:
    analyze_image(image_path: str, claim_text: Optional[str] = None) -> ImageFindings

Both entrypoints share a single underlying implementation in ``analyze_image.py``.
"""

from __future__ import annotations

from typing import Optional

from .analyze_image import analyze_image
from .contracts import ImageInput, ImageFindings


def run(input: ImageInput) -> ImageFindings:
    """Canonical Module 2 entrypoint per architecture.md §6.

    Accepts typed ``ImageInput`` and returns structured ``ImageFindings``.
    Zero dependency on FastAPI, LangGraph, or other modules.

    Parameters
    ----------
    input : ImageInput
        Contains ``image_path`` and optional ``claim_text``.

    Returns
    -------
    ImageFindings
        Aggregated per-component findings (BLIP, CLIP, PaddleOCR, Smaug).
    """
    return analyze_image(
        image_path=input.image_path,
        claim_text=input.claim_text,
    )


__all__ = ["run", "analyze_image"]

