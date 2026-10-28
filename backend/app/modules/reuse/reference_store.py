"""
Module 5 — reference_store.py
Postgres `reference_media` table interface.

Architecture decision (§Module 5):
  - A Postgres table replaces document_forgery's blockchain hash registry.
  - The blockchain (IPFS + Ethereum) is cut entirely — no immutable
    on-chain ledger needed for misinformation provenance.
  - Supabase-managed Postgres is used (Module 9's storage decision).

Table schema (DDL is in backend/app/db/migrations/):
  reference_media (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sha256        TEXT NOT NULL UNIQUE,
    phash         TEXT NOT NULL,
    modality      TEXT NOT NULL,           -- 'image' | 'video_keyframe'
    source_url    TEXT,
    published_at  TIMESTAMPTZ,
    source_location TEXT,
    caption       TEXT,
    inserted_at   TIMESTAMPTZ DEFAULT now()
  )
  CREATE INDEX ON reference_media (sha256);
  CREATE INDEX ON reference_media (phash);

Phase 1: sha256 exact-match + pHash Hamming scan.
Phase 3: widen returned MatchedSource to include
         source_url / source_published_at / source_location.
"""
from __future__ import annotations

import os
from typing import Optional

from .contracts import HammingTier, MatchedSource, Modality
from .hashing import hamming_distance, classify_hamming_tier, HAMMING_MODIFIED_THRESHOLD


def _get_client():
    """
    Lazy-import Supabase client to avoid import-time side effects during
    unit-testing (tests can mock this function).
    """
    from supabase import create_client
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_KEY"]
    return create_client(url, key)


# ---------------------------------------------------------------------------
# Read path — lookup
# ---------------------------------------------------------------------------

def lookup_by_sha256(sha256: str, client=None) -> Optional[MatchedSource]:
    """
    Exact-match lookup by SHA-256.  O(1) via the unique index.
    Returns a MatchedSource with hamming_distance=0 / tier=SAME on hit,
    None on miss.
    """
    client = client or _get_client()
    response = (
        client.table("reference_media")
        .select("id, sha256, phash, source_url, published_at, source_location, caption")
        .eq("sha256", sha256)
        .limit(1)
        .execute()
    )
    if not response.data:
        return None

    row = response.data[0]
    return MatchedSource(
        reference_id=row["id"],
        sha256_match=True,
        phash_hamming=0,
        hamming_tier=HammingTier.SAME,
        # Phase 3 fields — populated from DB even in Phase 1 build,
        # but consumers should treat them as None until Phase 3 wiring.
        source_url=row.get("source_url"),
        source_published_at=str(row["published_at"]) if row.get("published_at") else None,
        source_location=row.get("source_location"),
        reference_caption=row.get("caption"),
    )


def lookup_by_phash(
    query_phash: str,
    modality: Modality = Modality.IMAGE,
    max_hamming: int = HAMMING_MODIFIED_THRESHOLD,
    limit: int = 50,
    client=None,
) -> list[MatchedSource]:
    """
    Scan the reference_media table for pHash matches within `max_hamming`
    Hamming distance.

    Implementation note: Postgres has no native pHash index; we fetch a
    bounded candidate set (ordered by insertion) and filter in Python.
    For a large reference store (>100k rows) this should be replaced with
    a pgvector bit-vector index or a dedicated vantage-point tree.
    For Phase 1 (small seeded set) this is sufficient.

    Returns a list of MatchedSource, sorted ascending by phash_hamming.
    """
    client = client or _get_client()
    response = (
        client.table("reference_media")
        .select("id, sha256, phash, source_url, published_at, source_location, caption")
        .eq("modality", modality.value)
        .limit(limit)
        .execute()
    )

    matches: list[MatchedSource] = []
    for row in response.data or []:
        try:
            dist = hamming_distance(query_phash, row["phash"])
        except ValueError:
            # Hash-size mismatch — skip this row; can happen if the DB was
            # seeded with hashes computed at a different hash_size.
            continue

        if dist > max_hamming:
            continue

        tier = classify_hamming_tier(dist)
        matches.append(
            MatchedSource(
                reference_id=row["id"],
                sha256_match=False,
                phash_hamming=dist,
                hamming_tier=tier,
                source_url=row.get("source_url"),
                source_published_at=str(row["published_at"]) if row.get("published_at") else None,
                source_location=row.get("source_location"),
                reference_caption=row.get("caption"),
            )
        )

    matches.sort(key=lambda m: m.phash_hamming)
    return matches


# ---------------------------------------------------------------------------
# Write path — ingest a new reference into the store
# ---------------------------------------------------------------------------

def insert_reference(
    sha256: str,
    phash: str,
    modality: Modality,
    source_url: Optional[str] = None,
    published_at: Optional[str] = None,
    source_location: Optional[str] = None,
    caption: Optional[str] = None,
    client=None,
) -> str:
    """
    Insert a new reference-media record. Returns the generated UUID.
    Silently ignores duplicate SHA-256 conflicts (upsert on sha256).

    Used by the seed script (backend/scripts/seed_reference_media.py)
    and the optional admin ingest endpoint.
    """
    client = client or _get_client()
    payload = {
        "sha256": sha256,
        "phash": phash,
        "modality": modality.value,
        "source_url": source_url,
        "published_at": published_at,
        "source_location": source_location,
        "caption": caption,
    }
    response = (
        client.table("reference_media")
        .upsert(payload, on_conflict="sha256")
        .execute()
    )
    return response.data[0]["id"]
