"""
api/v1/reference.py — GET /api/v1/reference/lookup

Manual hash/pHash lookup against Module 5's reference_media store.

Accepts a SHA-256 hex digest or a pHash hex string and returns the
matching reference_media rows (source URL, publication date, caption).

This is a read-only endpoint — adding new reference media is an
admin/seeding operation, not an upload endpoint.
"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter()


# ── Response models ───────────────────────────────────────────────────────────

class ReferenceMediaRow(BaseModel):
    id:               Optional[str]  = None
    sha256:           Optional[str]  = None
    phash:            Optional[str]  = None
    source_url:       Optional[str]  = None
    published_at:     Optional[str]  = None
    source_location:  Optional[str]  = None
    caption:          Optional[str]  = None
    modality:         Optional[str]  = None  # image | video | audio


class ReferenceLookupResponse(BaseModel):
    query_sha256:  Optional[str]     = None
    query_phash:   Optional[str]     = None
    matches:       list[ReferenceMediaRow] = []
    total:         int               = 0


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.get("/reference/lookup", response_model=ReferenceLookupResponse)
async def reference_lookup(
    sha256: Optional[str] = Query(
        None,
        description="Exact SHA-256 hex digest to look up.",
        min_length=64,
        max_length=64,
    ),
    phash: Optional[str] = Query(
        None,
        description="pHash hex string to look up (exact match against stored hashes).",
    ),
    hamming_threshold: int = Query(
        5,
        ge=0,
        le=64,
        description="Max Hamming distance for pHash similarity (default 5 = 'same' tier).",
    ),
):
    """
    Look up media in Module 5's reference store by SHA-256 or pHash.

    At least one of `sha256` or `phash` must be provided.
    pHash lookup uses Hamming-distance comparison — `hamming_threshold`
    controls strictness (default 5 = Hamming < 5, the 'same' tier).
    """
    if not sha256 and not phash:
        raise HTTPException(400, "Provide at least one of `sha256` or `phash`.")

    matches: list[dict[str, Any]] = []

    try:
        from app.core.supabase_client import get_supabase
        sb = get_supabase()

        if sha256:
            # Exact hash match
            resp = (
                sb.table("reference_media")
                  .select("*")
                  .eq("sha256", sha256)
                  .execute()
            )
            matches.extend(resp.data or [])

        if phash and not matches:
            # pHash lookup — fetch all rows and compute Hamming distance in Python.
            # For large reference stores, delegate to a Postgres function or pgvector.
            resp = sb.table("reference_media").select("*").not_.is_("phash", "null").execute()
            all_rows = resp.data or []
            matches.extend(_filter_by_hamming(all_rows, phash, hamming_threshold))

    except RuntimeError:
        # Supabase not configured (local dev without env vars)
        return ReferenceLookupResponse(
            query_sha256=sha256,
            query_phash=phash,
            matches=[],
            total=0,
        )

    rows = [ReferenceMediaRow(**row) for row in matches]
    return ReferenceLookupResponse(
        query_sha256=sha256,
        query_phash=phash,
        matches=rows,
        total=len(rows),
    )


def _filter_by_hamming(
    rows: list[dict],
    query_phash_hex: str,
    threshold: int,
) -> list[dict]:
    """
    Filter `rows` by Hamming distance between their `phash` field and
    `query_phash_hex`.  Pure-Python implementation using imagehash.
    """
    try:
        import imagehash
        q_hash = imagehash.hex_to_hash(query_phash_hex)
        result = []
        for row in rows:
            stored_hex = row.get("phash")
            if not stored_hex:
                continue
            try:
                s_hash   = imagehash.hex_to_hash(stored_hex)
                distance = q_hash - s_hash
                if distance <= threshold:
                    row = dict(row)
                    row["hamming_distance"] = distance
                    result.append(row)
            except Exception:
                continue
        return sorted(result, key=lambda r: r.get("hamming_distance", 999))
    except ImportError:
        # imagehash not installed — return exact hex matches only
        return [r for r in rows if r.get("phash") == query_phash_hex]
