"""
modules/reuse/reference_store.py — Supabase reference_media queries (Module 5).

Provides two lookup functions:
  - exact_sha256_lookup(sha256)   → row dict or None
  - phash_nearest(phash_hex, threshold) → list of (distance, row) sorted by distance

Also exposes seed_reference_media() for populating the store during setup.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


def _get_sb():
    """Return the Supabase client, or raise if not configured."""
    from app.core.supabase_client import get_supabase
    return get_supabase()


# ── Exact SHA-256 lookup ──────────────────────────────────────────────────────

def exact_sha256_lookup(sha256: str) -> Optional[dict[str, Any]]:
    """
    Look up a media item by its exact SHA-256 digest.
    Returns the first matching reference_media row, or None.
    """
    try:
        sb   = _get_sb()
        resp = (
            sb.table("reference_media")
              .select("*")
              .eq("sha256", sha256)
              .limit(1)
              .execute()
        )
        rows = resp.data or []
        return rows[0] if rows else None
    except Exception as exc:       # noqa: BLE001
        logger.debug("exact_sha256_lookup failed: %s", exc)
        return None


# ── pHash nearest-neighbour lookup ────────────────────────────────────────────

def phash_nearest(
    query_phash_hex: str,
    threshold: int = 15,
    limit: int = 5,
) -> list[tuple[int, dict[str, Any]]]:
    """
    Fetch all reference_media rows that have a pHash, compute Hamming
    distance to *query_phash_hex*, and return those within *threshold*,
    sorted by ascending distance.

    Returns: [(distance, row_dict), ...]

    For large reference stores, delegate this to a Postgres function or
    a bit-count index (e.g. with the `pg_trgm` extension on the hex string
    or a custom SQL function). For the demo size (<10 k rows) Python-side
    filtering is acceptable.
    """
    try:
        import imagehash
        q_hash = imagehash.hex_to_hash(query_phash_hex)
    except Exception as exc:       # noqa: BLE001
        logger.debug("phash_nearest: bad query hash: %s", exc)
        return []

    try:
        sb   = _get_sb()
        resp = (
            sb.table("reference_media")
              .select("*")
              .not_.is_("phash", "null")
              .execute()
        )
        rows = resp.data or []
    except Exception as exc:       # noqa: BLE001
        logger.debug("phash_nearest DB fetch failed: %s", exc)
        return []

    results: list[tuple[int, dict]] = []
    for row in rows:
        stored_hex = row.get("phash", "")
        if not stored_hex:
            continue
        try:
            import imagehash as _ih
            s_hash   = _ih.hex_to_hash(stored_hex)
            distance = int(q_hash - s_hash)
            if distance <= threshold:
                results.append((distance, row))
        except Exception:
            continue

    results.sort(key=lambda t: t[0])
    return results[:limit]


# ── Seed helper ───────────────────────────────────────────────────────────────

def seed_reference_media(entries: list[dict[str, Any]]) -> int:
    """
    Insert or upsert a batch of reference_media entries.
    Each entry dict should have at least one of: sha256, phash, source_url.
    Returns the number of rows successfully upserted.
    """
    if not entries:
        return 0
    try:
        sb   = _get_sb()
        resp = (
            sb.table("reference_media")
              .upsert(entries, on_conflict="sha256")
              .execute()
        )
        return len(resp.data or [])
    except Exception as exc:       # noqa: BLE001
        logger.warning("seed_reference_media failed: %s", exc)
        return 0
