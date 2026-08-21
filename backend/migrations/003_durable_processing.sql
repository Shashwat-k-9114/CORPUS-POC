ALTER TABLE processing_jobs
    ADD COLUMN IF NOT EXISTS attempt_count INTEGER NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
    ADD COLUMN IF NOT EXISTS next_attempt_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS lease_acquired_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS heartbeat_at TIMESTAMPTZ;

ALTER TABLE page_checkpoints
    ADD COLUMN IF NOT EXISTS next_attempt_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS json_representation_id UUID,
    ADD COLUMN IF NOT EXISTS render_representation_id UUID;

ALTER TABLE page_checkpoints DROP CONSTRAINT IF EXISTS page_checkpoints_state_check;
ALTER TABLE page_checkpoints
    ADD CONSTRAINT page_checkpoints_state_check
    CHECK (state IN ('pending', 'queued', 'processing', 'completed', 'failed'));

ALTER TABLE derived_representations
    ADD COLUMN IF NOT EXISTS custodian_id UUID,
    ADD COLUMN IF NOT EXISTS canonical_object_id UUID,
    ADD COLUMN IF NOT EXISTS canonical_sha256 CHAR(64),
    ADD COLUMN IF NOT EXISTS settings_digest CHAR(64);

UPDATE derived_representations AS d
SET custodian_id = s.custodian_id,
    canonical_object_id = s.canonical_object_id,
    canonical_sha256 = c.sha256,
    settings_digest = encode(sha256(convert_to(d.settings::text, 'UTF8')), 'hex')
FROM sources AS s
JOIN canonical_objects AS c ON c.id = s.canonical_object_id
WHERE d.source_id = s.id
  AND (d.custodian_id IS NULL OR d.canonical_object_id IS NULL OR d.canonical_sha256 IS NULL OR d.settings_digest IS NULL);

ALTER TABLE derived_representations
    ALTER COLUMN custodian_id SET NOT NULL,
    ALTER COLUMN canonical_object_id SET NOT NULL,
    ALTER COLUMN canonical_sha256 SET NOT NULL,
    ALTER COLUMN settings_digest SET NOT NULL;

ALTER TABLE derived_representations
    DROP CONSTRAINT IF EXISTS derived_representations_custodian_fk,
    DROP CONSTRAINT IF EXISTS derived_representations_canonical_fk;
ALTER TABLE derived_representations
    ADD CONSTRAINT derived_representations_custodian_fk
        FOREIGN KEY (custodian_id) REFERENCES custodians(id) ON DELETE RESTRICT,
    ADD CONSTRAINT derived_representations_canonical_fk
        FOREIGN KEY (canonical_object_id) REFERENCES canonical_objects(id) ON DELETE RESTRICT;

ALTER TABLE page_checkpoints
    DROP CONSTRAINT IF EXISTS page_checkpoints_json_representation_fk,
    DROP CONSTRAINT IF EXISTS page_checkpoints_render_representation_fk;
ALTER TABLE page_checkpoints
    ADD CONSTRAINT page_checkpoints_json_representation_fk
        FOREIGN KEY (json_representation_id) REFERENCES derived_representations(id) ON DELETE RESTRICT,
    ADD CONSTRAINT page_checkpoints_render_representation_fk
        FOREIGN KEY (render_representation_id) REFERENCES derived_representations(id) ON DELETE RESTRICT;

CREATE TABLE IF NOT EXISTS worker_heartbeats (
    worker_id TEXT PRIMARY KEY,
    started_at TIMESTAMPTZ NOT NULL,
    last_seen_at TIMESTAMPTZ NOT NULL,
    status TEXT NOT NULL,
    active_job_id UUID REFERENCES processing_jobs(id) ON DELETE SET NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_jobs_claimable
    ON processing_jobs (state, next_attempt_at, priority DESC, created_at, id);
CREATE INDEX IF NOT EXISTS idx_checkpoints_job_page_state
    ON page_checkpoints (job_id, page_number, state);
CREATE INDEX IF NOT EXISTS idx_representations_custodian_source
    ON derived_representations (custodian_id, source_id, page_number, representation_kind);
