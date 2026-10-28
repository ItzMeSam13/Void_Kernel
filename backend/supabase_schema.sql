-- ============================================================
-- Supabase Schema — Void Kernel Misinformation Detector
-- architecture.md §Module 9 — Storage decision: Supabase
-- Run in the Supabase SQL editor or with `supabase db push`
-- ============================================================

-- Enable pgvector for future claim-embedding drift guard
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================
-- Table: jobs
-- One row per submitted media file / analysis request.
-- ============================================================
CREATE TABLE IF NOT EXISTS jobs (
    id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at     TIMESTAMPTZ NOT NULL    DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL    DEFAULT now(),

    -- Media identity
    sha256         TEXT        NOT NULL,       -- hex SHA-256 of raw upload bytes
    filename       TEXT,
    modality       TEXT        NOT NULL        -- text_image | video | audio_only
                   CHECK (modality IN ('text_image', 'video', 'audio_only')),

    -- User input
    claim_text     TEXT,                       -- user-supplied caption / claim (nullable)

    -- Pipeline status
    status         TEXT        NOT NULL DEFAULT 'queued'
                   CHECK (status IN ('queued', 'processing', 'done', 'failed')),

    -- Storage path for the original upload (Supabase Storage bucket: media)
    media_storage_path  TEXT,

    -- Full fusion_output JSON (stored here for fast polling without joins)
    result_json    JSONB,

    -- Top-level error message if status = 'failed'
    error          TEXT
);

CREATE INDEX IF NOT EXISTS jobs_sha256_idx  ON jobs (sha256);
CREATE INDEX IF NOT EXISTS jobs_status_idx  ON jobs (status);
CREATE INDEX IF NOT EXISTS jobs_created_idx ON jobs (created_at DESC);

-- Auto-update updated_at on every write
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS jobs_updated_at ON jobs;
CREATE TRIGGER jobs_updated_at
    BEFORE UPDATE ON jobs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();


-- ============================================================
-- Table: module_findings
-- Granular per-module result rows linked to a job.
-- Allows Module 8 to query findings across many jobs.
-- ============================================================
CREATE TABLE IF NOT EXISTS module_findings (
    id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id     UUID        NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    module     TEXT        NOT NULL,   -- image | video | audio | reuse | factcheck | fusion | text
    axis       TEXT,                   -- veracity | authenticity | consistency | reuse (for fusion rows)
    verdict    TEXT,
    confidence REAL,
    findings   JSONB,                  -- full typed findings dict for the module
    error      TEXT
);

CREATE INDEX IF NOT EXISTS module_findings_job_idx    ON module_findings (job_id);
CREATE INDEX IF NOT EXISTS module_findings_module_idx ON module_findings (module);


-- ============================================================
-- Table: reference_media
-- Module 5 — hash/pHash reference store for historical reuse.
-- architecture.md §Module 5: "minus the blockchain itself"
-- ============================================================
CREATE TABLE IF NOT EXISTS reference_media (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- Fingerprints
    sha256          TEXT        UNIQUE,       -- exact-match hash
    phash           TEXT,                     -- perceptual hash hex string (DCT-based)

    -- Source provenance
    source_url      TEXT,
    published_at    TIMESTAMPTZ,
    source_location TEXT,                     -- location stated on the matched page/article
    caption         TEXT,                     -- caption / description on the source page
    modality        TEXT                      -- image | video | audio
                    CHECK (modality IN ('image', 'video', 'audio')),

    -- Supabase Storage path for the reference media file itself (optional)
    storage_path    TEXT
);

CREATE INDEX IF NOT EXISTS reference_media_sha256_idx ON reference_media (sha256);
CREATE INDEX IF NOT EXISTS reference_media_phash_idx  ON reference_media (phash);


-- ============================================================
-- Table: evidence_sources
-- Module 6 — per-claim evidence items (web search results,
-- fact-check API hits, entity agreement flags).
-- ============================================================
CREATE TABLE IF NOT EXISTS evidence_sources (
    id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id         UUID        NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),

    claim_text     TEXT,                -- the atomic claim this evidence pertains to
    source_url     TEXT,
    source_type    TEXT,                -- web_search | fact_check_api | module5_match
    stance         TEXT,                -- supported | contradicted | neutral | unknown
    relevance_score REAL,
    snippet        TEXT,                -- excerpt from the source page
    echo_chamber   BOOLEAN DEFAULT FALSE,  -- true if flagged by echo-chamber detection
    raw_metadata   JSONB
);

CREATE INDEX IF NOT EXISTS evidence_sources_job_idx ON evidence_sources (job_id);


-- ============================================================
-- Table: eval_reports
-- Module 8 — per-module evaluation results surfaced in the
-- analytics dashboard (GET /api/v1/eval/{module}).
-- ============================================================
CREATE TABLE IF NOT EXISTS eval_reports (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),

    module              TEXT        NOT NULL,  -- image | video | audio | reuse | factcheck | fusion | text
    accuracy            REAL,
    f1_score            REAL,
    false_positive_rate REAL,
    latency_ms_p95      REAL,
    sample_count        INTEGER,
    notes               TEXT,
    raw_report          JSONB                 -- full eval_report.json for the frontend
);

CREATE INDEX IF NOT EXISTS eval_reports_module_idx ON eval_reports (module);
CREATE INDEX IF NOT EXISTS eval_reports_created_idx ON eval_reports (created_at DESC);


-- ============================================================
-- Supabase Storage buckets (create via dashboard or CLI)
-- architecture.md §Module 9 — "Supabase Storage buckets for
-- media/heatmaps"
--
-- Run these in Supabase SQL editor if the storage extension is enabled:
-- ============================================================

-- Raw uploaded media
INSERT INTO storage.buckets (id, name, public)
VALUES ('media', 'media', FALSE)
ON CONFLICT (id) DO NOTHING;

-- Saliency heatmaps + spatial attention overlays from Module 3
INSERT INTO storage.buckets (id, name, public)
VALUES ('heatmaps', 'heatmaps', TRUE)
ON CONFLICT (id) DO NOTHING;


-- ============================================================
-- Row-level security (basic — tighten before production)
-- ============================================================

ALTER TABLE jobs             ENABLE ROW LEVEL SECURITY;
ALTER TABLE module_findings  ENABLE ROW LEVEL SECURITY;
ALTER TABLE reference_media  ENABLE ROW LEVEL SECURITY;
ALTER TABLE evidence_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE eval_reports     ENABLE ROW LEVEL SECURITY;

-- Service role (used by backend) bypasses RLS automatically.
-- Anon / authenticated roles get read access to results, no write.

CREATE POLICY "public read jobs" ON jobs
    FOR SELECT USING (true);

CREATE POLICY "public read module_findings" ON module_findings
    FOR SELECT USING (true);

CREATE POLICY "public read reference_media" ON reference_media
    FOR SELECT USING (true);

CREATE POLICY "public read evidence_sources" ON evidence_sources
    FOR SELECT USING (true);

CREATE POLICY "public read eval_reports" ON eval_reports
    FOR SELECT USING (true);
