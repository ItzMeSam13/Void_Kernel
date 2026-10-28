#!/usr/bin/env python3
"""
Seed script: populate reference_media with a small curated set of
known viral / reused media for the demo.

Architecture §Module 5, Step 3:
  "Seed it with a small curated set of known viral/reused media for
   the demo."

Usage:
  SUPABASE_URL=... SUPABASE_SERVICE_KEY=... python scripts/seed_reference_media.py

Each entry below should have a real local image path pointing to
a downloaded sample. The script computes the fingerprints itself
and inserts via reference_store.insert_reference().

Add more entries to SEED_ITEMS as the demo set grows.
"""
from __future__ import annotations

import os
import sys

# Allow running from the backend/ directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.modules.reuse.hashing import fingerprint
from app.modules.reuse.reference_store import insert_reference
from app.modules.reuse.contracts import Modality


# ---------------------------------------------------------------------------
# Seed data — update local_path / metadata before running
# ---------------------------------------------------------------------------
SEED_ITEMS: list[dict] = [
    # Example entry — replace local_path with a real downloaded image.
    {
        "local_path": "scripts/sample_media/sample1.jpg",
        "modality": Modality.IMAGE,
        "source_url": "https://example.com/viral-image-1",
        "published_at": "2019-06-12T00:00:00Z",
        "source_location": "New Delhi, India",
        "caption": "Crowd during a 2019 election rally — frequently reused out of context.",
    },
    # Add more entries here...
]


def main() -> None:
    inserted = 0
    skipped = 0

    for item in SEED_ITEMS:
        path = item["local_path"]
        if not os.path.exists(path):
            print(f"[SKIP] File not found: {path}")
            skipped += 1
            continue

        try:
            sha256, phash = fingerprint(path)
            ref_id = insert_reference(
                sha256=sha256,
                phash=phash,
                modality=item["modality"],
                source_url=item.get("source_url"),
                published_at=item.get("published_at"),
                source_location=item.get("source_location"),
                caption=item.get("caption"),
            )
            print(f"[OK] Inserted {path} → id={ref_id}")
            inserted += 1
        except Exception as exc:
            print(f"[ERR] {path}: {exc}")
            skipped += 1

    print(f"\nDone: {inserted} inserted, {skipped} skipped.")


if __name__ == "__main__":
    main()
