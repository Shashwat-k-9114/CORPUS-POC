CREATE TABLE IF NOT EXISTS admission_requests (
    id UUID PRIMARY KEY,
    custodian_id UUID NOT NULL REFERENCES custodians(id) ON DELETE RESTRICT,
    idempotency_key TEXT NOT NULL,
    request_fingerprint CHAR(64) NOT NULL CHECK (request_fingerprint ~ '^[0-9a-f]{64}$'),
    source_id UUID NOT NULL REFERENCES sources(id) ON DELETE RESTRICT,
    canonical_object_id UUID NOT NULL REFERENCES canonical_objects(id) ON DELETE RESTRICT,
    arrival_id UUID NOT NULL REFERENCES source_arrivals(id) ON DELETE RESTRICT,
    enrollment_id UUID NOT NULL REFERENCES enrollments(id) ON DELETE RESTRICT,
    processing_job_id UUID NOT NULL REFERENCES processing_jobs(id) ON DELETE RESTRICT,
    exact_duplicate BOOLEAN NOT NULL,
    completed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (custodian_id, idempotency_key)
);

WITH active_ranked AS (
    SELECT id,
           row_number() OVER (PARTITION BY source_id ORDER BY created_at, id) AS rank
    FROM processing_jobs
    WHERE state IN ('queued', 'processing')
)
UPDATE processing_jobs AS jobs
SET state = 'failed',
    last_error = 'Superseded duplicate active job during admission migration',
    updated_at = now()
FROM active_ranked
WHERE jobs.id = active_ranked.id
  AND active_ranked.rank > 1;

CREATE UNIQUE INDEX IF NOT EXISTS uq_processing_jobs_active_source
    ON processing_jobs (source_id)
    WHERE state IN ('queued', 'processing');

CREATE INDEX IF NOT EXISTS idx_admission_requests_source
    ON admission_requests (custodian_id, source_id, completed_at DESC);
