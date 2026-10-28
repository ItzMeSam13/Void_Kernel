<<<<<<< HEAD
# Module 5 — Historical / Out-of-Context Reuse
=======
"""
modules/reuse/__init__.py — Module 5: Historical / Out-of-Context Reuse.

Public entrypoint: run(ReuseInput) → ReuseFindings

Implementation (architecture.md §Module 5):
  1. Compute SHA-256 of file bytes → exact-match lookup in reference_media.
  2. Compute pHash → Hamming-distance nearest-neighbour lookup, tier assignment.
  3. Populate source_url / source_published_at / source_location from match row.
  4. (Optional, feature-flagged) SerpApi reverse-image search.

Isolation rule: this module calls hashing.py and reference_store.py only.
It has zero knowledge of other modules or the orchestration layer.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from app.modules.reuse.contracts import ReuseInput, ReuseFindings
from app.modules.reuse.hashing import (
    compute_sha256,
    compute_phash,
    hamming_distance,
    phash_tier,
    SAME_THRESHOLD,
    MODIFIED_THRESHOLD,
)
from app.modules.reuse.reference_store import exact_sha256_lookup, phash_nearest

logger = logging.getLogger(__name__)


async def run(inp: ReuseInput) -> ReuseFindings:
    """
    Module 5 entrypoint.

    Accepts either:
      - inp.sha256 + inp.media_path  (sha256 pre-computed by the ingest layer)
      - inp.media_path alone         (sha256 + pHash computed here)
      - inp.image_bytes alone        (for per-frame calls from Module 3)

    Returns ReuseFindings with source provenance populated when a match is found.
    """
    try:
        # ── 1. Resolve raw bytes ──────────────────────────────────────────────
        raw_bytes = await _resolve_bytes(inp)
        if raw_bytes is None and inp.sha256 is None:
            return ReuseFindings(error="No media bytes or sha256 provided.")

        # ── 2. SHA-256 ────────────────────────────────────────────────────────
        sha = inp.sha256 or (compute_sha256(raw_bytes) if raw_bytes else None)

        # ── 3. Exact SHA-256 lookup ───────────────────────────────────────────
        if sha:
            exact_row = exact_sha256_lookup(sha)
            if exact_row:
                return _build_exact_match(exact_row)

        # ── 4. pHash lookup ───────────────────────────────────────────────────
        if raw_bytes:
            phash_hex = compute_phash(raw_bytes)
        elif inp.media_path:
            phash_hex = _phash_from_path(inp.media_path)
        else:
            phash_hex = None

        if phash_hex:
            nearest = phash_nearest(phash_hex, threshold=MODIFIED_THRESHOLD)
            if nearest:
                distance, row = nearest[0]
                tier = phash_tier(distance)
                return _build_phash_match(phash_hex, distance, tier, row)

        # ── 5. No match ───────────────────────────────────────────────────────
        return ReuseFindings(
            exact_match=False,
            reuse_tier="different",
        )

    except Exception as exc:       # noqa: BLE001
        logger.exception("Module 5 run() error: %s", exc)
        return ReuseFindings(error=str(exc))


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _resolve_bytes(inp: ReuseInput) -> Optional[bytes]:
    """Read raw bytes from the input, trying image_bytes then media_path."""
    if inp.image_bytes:
        return inp.image_bytes
    if inp.media_path:
        try:
            return Path(inp.media_path).read_bytes()
        except OSError as exc:
            logger.debug("_resolve_bytes read error: %s", exc)
            return None
    return None


def _phash_from_path(path: str) -> Optional[str]:
    try:
        return compute_phash(Path(path).read_bytes())
    except Exception:
        return None


def _build_exact_match(row: dict) -> ReuseFindings:
    """Build a ReuseFindings for a SHA-256 exact hit."""
    return ReuseFindings(
        exact_match=True,
        phash_hamming_distance=0,
        reuse_tier="same",
        source_url=row.get("source_url"),
        source_published_at=str(row["published_at"]) if row.get("published_at") else None,
        source_location=row.get("source_location"),
        source_caption=row.get("caption"),
    )


def _build_phash_match(
    phash_hex: str,
    distance: int,
    tier: str,
    row: dict,
) -> ReuseFindings:
    """Build a ReuseFindings for a pHash nearest-neighbour hit."""
    return ReuseFindings(
        exact_match=False,
        phash_hamming_distance=distance,
        reuse_tier=tier,                 # type: ignore[arg-type]
        source_url=row.get("source_url"),
        source_published_at=str(row["published_at"]) if row.get("published_at") else None,
        source_location=row.get("source_location"),
        source_caption=row.get("caption"),
    )
>>>>>>> d3d2c45df93abffce0459e62fed0f32a1920cf8f
