"""
modules/reuse/contracts.py — Module 5 public contracts (Person 1 owns this).

ReuseInput / ReuseFindings form the ONLY interface surface of Module 5.
"""
from __future__ import annotations

from typing import Any, Literal, Optional
from pydantic import BaseModel, Field


ReuseTier = Literal["same", "modified", "different"]


class ReuseInput(BaseModel):
    """Input to Module 5's run() entrypoint."""
    media_path:  Optional[str]  = Field(None, description="Local path to the media file.")
    sha256:      Optional[str]  = Field(None, description="Pre-computed SHA-256 to skip recomputation.")
    image_bytes: Optional[bytes] = Field(None, description="Raw image bytes for pHash (alternative to path).")


class ReuseFindings(BaseModel):
    """
    Output of Module 5's run() entrypoint.
    Matches the stub in orchestrator/state.py — keep in sync.
    """
    exact_match:           bool              = False
    phash_hamming_distance: Optional[int]   = Field(None,
        description="Hamming distance to closest match in reference store.")
    reuse_tier:            Optional[ReuseTier] = Field(None,
        description="same (<5) | modified (5–15) | different (>15)")

    # Source provenance from matched reference_media row
    source_url:            Optional[str]    = None
    source_published_at:   Optional[str]    = None
    source_location:       Optional[str]    = None
    source_caption:        Optional[str]    = None

    # Optional reverse-image search results (SerpApi — feature-flagged)
    reverse_image_results: list[dict[str, Any]] = Field(default_factory=list)

    error:                 Optional[str]    = None
