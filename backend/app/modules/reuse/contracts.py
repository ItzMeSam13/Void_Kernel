"""
Module 5 — Historical / Out-of-Context Reuse
Pydantic contracts (input + output). No logic lives here.

Architecture §6 contract-first rule:
  - ReuseInput   — what callers hand to Module 5
  - ReuseFindings — what Module 5 returns; frozen at end of Phase 1
    so Persons 2 & 3 can call it and 1B can wire it into GraphState.

Phase 3 additions are marked [PHASE-3] so the schema can be widened
without breaking Phase 1 consumers (they just ignore the new optional
fields, which default to None).
"""
from __future__ import annotations

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class HammingTier(str, Enum):
    """
    Hamming-distance tiers ported directly from document_forgery's provenance
    layer (architecture.md §Asset Reuse Matrix).

    < 5  → effectively the same image
    5–15 → modified / cropped / recompressed version of the same image
    > 15 → different image (no useful match)
    """
    SAME = "same"           # hamming distance < 5
    MODIFIED = "modified"   # 5 ≤ hamming distance ≤ 15
    DIFFERENT = "different" # hamming distance > 15


class Modality(str, Enum):
    IMAGE = "image"
    VIDEO_KEYFRAME = "video_keyframe"
    DOCUMENT = "document"


# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------

class ReuseInput(BaseModel):
    """
    Callers (Module 2, Module 3 per-frame) pass either raw bytes or a local
    file path.  Exactly one of `image_bytes` or `image_path` must be set.
    """
    image_bytes: Optional[bytes] = Field(
        default=None,
        description="Raw image bytes. Mutually exclusive with image_path.",
    )
    image_path: Optional[str] = Field(
        default=None,
        description="Absolute path to a local image file. Mutually exclusive with image_bytes.",
    )
    modality: Modality = Field(
        default=Modality.IMAGE,
        description="Whether the media is a standalone image or a video keyframe.",
    )

    model_config = {"arbitrary_types_allowed": True}


# ---------------------------------------------------------------------------
# Output — ReuseFindings
# ---------------------------------------------------------------------------

class MatchedSource(BaseModel):
    """
    Structured metadata for a single reference-media match.

    Phase 1: sha256_match + phash_hamming + hamming_tier are always populated.
    Phase 3: source_url / source_published_at / source_location are widened
    from the reference_media table (architecture.md Module 5 [Improvement]).
    """
    reference_id: str = Field(description="Primary key of the matched row in reference_media.")
    sha256_match: bool = Field(description="True if exact SHA-256 hash matched.")
    phash_hamming: int = Field(
        description="Hamming distance between the query pHash and the matched reference pHash."
    )
    hamming_tier: HammingTier

    # [PHASE-3] — widened source metadata; None until Phase 3 wiring is done.
    source_url: Optional[str] = None
    source_published_at: Optional[str] = None   # ISO-8601 string; None if unknown
    source_location: Optional[str] = None        # free-text location stated on source
    reference_caption: Optional[str] = None


class ReuseFindings(BaseModel):
    """
<<<<<<< HEAD
    Top-level output contract for Module 5.

    Architecture rule (§6): this is the *entire* interface surface of Module 5.
    No other module reaches inside; they consume only this schema.
    """
    reused: bool = Field(
        description=(
            "True when at least one reference match with hamming_tier SAME or MODIFIED "
            "was found in the local store (or via reverse-image API when enabled)."
        )
    )
    best_match: Optional[MatchedSource] = Field(
        default=None,
        description="The highest-confidence match, or None when reused=False.",
    )
    all_matches: list[MatchedSource] = Field(
        default_factory=list,
        description="All matches found (hamming_tier != DIFFERENT), ordered by hamming distance.",
    )

    # Query fingerprints — useful for callers that want to store them.
    query_sha256: str = Field(description="SHA-256 hex digest of the queried image.")
    query_phash: str = Field(description="Perceptual hash hex string of the queried image.")

    # Reverse-image API (optional, feature-flagged, Phase 4)
    reverse_search_used: bool = False
    reverse_search_results: list[dict] = Field(default_factory=list)

    error: Optional[str] = Field(
        default=None,
        description=(
            "Set to a human-readable message when the lookup could not complete. "
            "Guiding Principle 4: fail honest, never silent."
        ),
    )
=======
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
>>>>>>> d3d2c45df93abffce0459e62fed0f32a1920cf8f
