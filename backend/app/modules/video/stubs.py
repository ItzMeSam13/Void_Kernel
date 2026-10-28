"""
Module 3 — Cross-module boundary stubs.

Contains:
  1. ImageFindings — agreed stub shape for Person 3's Module 2 output.
  2. ReuseFindings — agreed stub shape for Person 1's Module 5 output.
  3. fake_* functions — stand-ins exercising the call sites end-to-end.
  4. analyze_image_fn / reuse_lookup_fn — the swap points.

To replace a stub with the real implementation:
  from app.modules.image.contracts import ImageFindings          # Person 3
  from app.modules.reuse.contracts import ReuseFindings          # Person 1
  from app.modules.image.run import analyze_image as real_fn
  from app.modules.reuse.reference_store import lookup as real_lookup
  analyze_image_fn = real_fn
  reuse_lookup_fn  = real_lookup

No other code changes required — all call sites already use the hook names.
"""

from __future__ import annotations

from typing import Callable, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Person 3 — Module 2 (Image Intelligence) stub contract
# Fields agreed from architecture.md Module 2 sub-tasks:
#   A1 BLIP caption · A2 CLIP similarity · A3 PaddleOCR (narrow + wide OCR)
#   A4 Smaug AI-image score · A5 ManTraNet manipulation score
# ---------------------------------------------------------------------------

class ImageFindings(BaseModel):
    caption: str = Field(default="", description="BLIP caption.")
    clip_similarity_score: Optional[float] = Field(
        default=None, ge=0.0, le=1.0,
        description="CLIP ViT-B/32 cosine similarity of image vs claim text.",
    )
    ocr_text: str = Field(default="", description="PaddleOCR embedded caption/meme text.")
    background_text: str = Field(
        default="",
        description=(
            "Incidental scene text (street signs, storefronts, banners) — "
            "Module 2 Phase 2 widened OCR, feeds Person 1's entity cross-check."
        ),
    )
    ai_generated_score: Optional[float] = Field(
        default=None, ge=0.0, le=1.0,
        description="Smaug AI-image detector score. Higher → more likely AI-generated.",
    )
    manipulation_score: Optional[float] = Field(
        default=None, ge=0.0, le=1.0,
        description="ManTraNet/BusterNet manipulation localization aggregate score.",
    )
    not_assessed: bool = Field(
        default=False,
        description="True when the module could not assess this crop (too small, model fail, etc.).",
    )


# ---------------------------------------------------------------------------
# Person 1 — Module 5 (Historical Reuse) stub contract
# Fields agreed from architecture.md Module 5 [Improvement]:
#   hash match tier + structured source metadata
# ---------------------------------------------------------------------------

class ReuseFindings(BaseModel):
    hash_match: bool = False
    phash_hamming_distance: Optional[int] = Field(
        default=None,
        description="Hamming distance to nearest known pHash. <5 = same, 5–15 = modified, >15 = different.",
    )
    reuse_tier: Optional[str] = Field(
        default=None, description="'same' | 'modified' | 'different' | None."
    )
    source_url: Optional[str] = None
    source_published_at: Optional[str] = None
    source_location: Optional[str] = None


# ---------------------------------------------------------------------------
# Stub implementations — exercised end-to-end until real modules land
# ---------------------------------------------------------------------------

def fake_analyze_image(
    face_crop_path: str,
    claim_text: Optional[str],
) -> ImageFindings:
    """Returns placeholder ImageFindings. Swap for Person 3's analyze_image()."""
    return ImageFindings(
        caption="[stub — Person 3 module not yet integrated]",
        clip_similarity_score=None,
        ocr_text="",
        background_text="",
        ai_generated_score=None,
        manipulation_score=None,
        not_assessed=True,
    )


def fake_reuse_lookup(phash_hex: str) -> ReuseFindings:
    """Returns placeholder ReuseFindings. Swap for Person 1's Module 5 lookup()."""
    return ReuseFindings()


# ---------------------------------------------------------------------------
# Swap points — change these two lines when real modules land
# ---------------------------------------------------------------------------

try:
    from app.modules.image.run import analyze_image as real_analyze_image
    analyze_image_fn: Optional[Callable] = real_analyze_image
except ImportError:
    analyze_image_fn: Optional[Callable] = fake_analyze_image
reuse_lookup_fn: Optional[Callable] = fake_reuse_lookup
