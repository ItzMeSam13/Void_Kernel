"""
modules/image/__init__.py — Module 2 public entrypoint (stub).

Person 3 implements analyze_image() here.
This stub returns a not-assessed ImageFindings so the orchestrator
can compile and run before Module 2 is finished.

Entrypoint signature (architecture.md §6):
  async def run(inp: ImageInput) -> ImageFindings
"""
from __future__ import annotations

from app.modules.image.contracts import ImageInput, ImageFindings


async def run(inp: ImageInput) -> ImageFindings:
    """
    STUB — Person 3 replaces this body.
    Calls BLIP caption, CLIP similarity, PaddleOCR, Smaug AI-image
    detector, and ManTraNet manipulation localization.
    Returns an ImageFindings with all fields populated.
    """
    return ImageFindings(
        error="Module 2 (image) not yet implemented — stub."
    )
