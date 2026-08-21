CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS custodians (
    id UUID PRIMARY KEY,
    slug TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS corpora (
    id UUID PRIMARY KEY,
    custodian_id UUID NOT NULL REFERENCES custodians(id) ON DELETE RESTRICT,
    name TEXT NOT NULL,
    kind TEXT NOT NULL CHECK (kind = 'custodian'),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (custodian_id, kind)
);

CREATE TABLE IF NOT EXISTS canonical_objects (
    id UUID PRIMARY KEY,
    custodian_id UUID NOT NULL REFERENCES custodians(id) ON DELETE RESTRICT,
    sha256 CHAR(64) NOT NULL CHECK (sha256 ~ '^[0-9a-f]{64}$'),
    byte_size BIGINT NOT NULL CHECK (byte_size >= 0),
    media_type TEXT NOT NULL,
    storage_key TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (custodian_id, sha256)
);

CREATE TABLE IF NOT EXISTS sources (
    id UUID PRIMARY KEY,
    custodian_id UUID NOT NULL REFERENCES custodians(id) ON DELETE RESTRICT,
    canonical_object_id UUID NOT NULL REFERENCES canonical_objects(id) ON DELETE RESTRICT,
    display_name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (custodian_id, canonical_object_id)
);

CREATE TABLE IF NOT EXISTS source_arrivals (
    id UUID PRIMARY KEY,
    source_id UUID NOT NULL REFERENCES sources(id) ON DELETE RESTRICT,
    claimed_origin TEXT NOT NULL,
    obtained_from TEXT NOT NULL,
    arrival_channel TEXT NOT NULL,
    original_filename TEXT,
    received_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS enrollments (
    id UUID PRIMARY KEY,
    corpus_id UUID NOT NULL REFERENCES corpora(id) ON DELETE RESTRICT,
    source_id UUID NOT NULL REFERENCES sources(id) ON DELETE RESTRICT,
    enrolled_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (corpus_id, source_id)
);

CREATE TABLE IF NOT EXISTS processing_jobs (
    id UUID PRIMARY KEY,
    source_id UUID NOT NULL REFERENCES sources(id) ON DELETE RESTRICT,
    pipeline_name TEXT NOT NULL,
    pipeline_version TEXT NOT NULL,
    state TEXT NOT NULL CHECK (state IN ('queued', 'processing', 'completed', 'partial', 'failed')),
    priority INTEGER NOT NULL DEFAULT 0,
    total_pages INTEGER CHECK (total_pages IS NULL OR total_pages >= 0),
    completed_pages INTEGER NOT NULL DEFAULT 0 CHECK (completed_pages >= 0),
    failed_pages INTEGER NOT NULL DEFAULT 0 CHECK (failed_pages >= 0),
    retry_count INTEGER NOT NULL DEFAULT 0 CHECK (retry_count >= 0),
    lease_owner TEXT,
    lease_expires_at TIMESTAMPTZ,
    last_error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS processing_attempts (
    id UUID PRIMARY KEY,
    job_id UUID NOT NULL REFERENCES processing_jobs(id) ON DELETE RESTRICT,
    attempt_number INTEGER NOT NULL CHECK (attempt_number > 0),
    worker_id TEXT NOT NULL,
    claimed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    heartbeat_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    ended_at TIMESTAMPTZ,
    outcome TEXT,
    error TEXT,
    UNIQUE (job_id, attempt_number)
);

CREATE TABLE IF NOT EXISTS page_checkpoints (
    id UUID PRIMARY KEY,
    job_id UUID NOT NULL REFERENCES processing_jobs(id) ON DELETE RESTRICT,
    page_number INTEGER NOT NULL CHECK (page_number > 0),
    state TEXT NOT NULL CHECK (state IN ('queued', 'processing', 'completed', 'failed')),
    attempt_count INTEGER NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
    representation_id UUID,
    last_error TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (job_id, page_number)
);

CREATE TABLE IF NOT EXISTS derived_representations (
    id UUID PRIMARY KEY,
    source_id UUID NOT NULL REFERENCES sources(id) ON DELETE RESTRICT,
    job_id UUID NOT NULL REFERENCES processing_jobs(id) ON DELETE RESTRICT,
    representation_kind TEXT NOT NULL,
    schema_version TEXT NOT NULL,
    storage_key TEXT NOT NULL UNIQUE,
    content_sha256 CHAR(64) NOT NULL CHECK (content_sha256 ~ '^[0-9a-f]{64}$'),
    byte_size BIGINT NOT NULL CHECK (byte_size >= 0),
    page_number INTEGER CHECK (page_number IS NULL OR page_number > 0),
    extractor_name TEXT NOT NULL,
    extractor_version TEXT NOT NULL,
    settings JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (job_id, representation_kind, page_number)
);

ALTER TABLE page_checkpoints
    DROP CONSTRAINT IF EXISTS page_checkpoints_representation_fk;
ALTER TABLE page_checkpoints
    ADD CONSTRAINT page_checkpoints_representation_fk
    FOREIGN KEY (representation_id) REFERENCES derived_representations(id) ON DELETE RESTRICT;

CREATE INDEX IF NOT EXISTS idx_sources_custodian ON sources(custodian_id);
CREATE INDEX IF NOT EXISTS idx_arrivals_source ON source_arrivals(source_id, received_at DESC);
CREATE INDEX IF NOT EXISTS idx_enrollments_corpus ON enrollments(corpus_id);
CREATE INDEX IF NOT EXISTS idx_jobs_state_priority ON processing_jobs(state, priority DESC, created_at);
CREATE INDEX IF NOT EXISTS idx_checkpoints_job_state ON page_checkpoints(job_id, state);
CREATE INDEX IF NOT EXISTS idx_representations_source ON derived_representations(source_id, created_at DESC);

INSERT INTO custodians (id, slug, name)
VALUES ('00000000-0000-0000-0000-000000000001', 'default', 'Default custodian')
ON CONFLICT (slug) DO NOTHING;

INSERT INTO corpora (id, custodian_id, name, kind)
SELECT '00000000-0000-0000-0000-000000000002', id, 'Default corpus', 'custodian'
FROM custodians WHERE slug = 'default'
ON CONFLICT (custodian_id, kind) DO NOTHING;
