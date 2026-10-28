-- Module 5: reference_media table
-- Run this against your Supabase Postgres instance.
-- Architecture §Module 5: "A Postgres table with the hash, pHash,
-- source metadata, and insertion timestamp — minus the blockchain."

CREATE TABLE IF NOT EXISTS reference_media (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sha256          TEXT NOT NULL,
    phash           TEXT NOT NULL,
    modality        TEXT NOT NULL CHECK (modality IN ('image', 'video_keyframe', 'document')),
    source_url      TEXT,
    published_at    TIMESTAMPTZ,
    source_location TEXT,
    caption         TEXT,
    inserted_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Unique constraint on sha256 — supports upsert in reference_store.insert_reference()
CREATE UNIQUE INDEX IF NOT EXISTS reference_media_sha256_idx ON reference_media (sha256);

-- pHash index — used by the candidate-scan lookup in reference_store.lookup_by_phash()
CREATE INDEX IF NOT EXISTS reference_media_phash_idx ON reference_media (phash);

-- Modality filter index
CREATE INDEX IF NOT EXISTS reference_media_modality_idx ON reference_media (modality);
