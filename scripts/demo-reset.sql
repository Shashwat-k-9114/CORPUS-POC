BEGIN;

CREATE TEMP TABLE demo_scope ON COMMIT DROP AS
SELECT id AS custodian_id
FROM custodians
WHERE slug = 'demo';

CREATE TEMP TABLE demo_sources ON COMMIT DROP AS
SELECT s.id AS source_id, s.canonical_object_id
FROM sources s
JOIN demo_scope d ON d.custodian_id = s.custodian_id;

CREATE TEMP TABLE demo_jobs ON COMMIT DROP AS
SELECT j.id AS job_id
FROM processing_jobs j
JOIN demo_sources s ON s.source_id = j.source_id;

UPDATE worker_heartbeats
SET active_job_id = NULL
WHERE active_job_id IN (SELECT job_id FROM demo_jobs);

DELETE FROM admission_requests
WHERE custodian_id IN (SELECT custodian_id FROM demo_scope);
DELETE FROM page_checkpoints
WHERE job_id IN (SELECT job_id FROM demo_jobs);
DELETE FROM processing_attempts
WHERE job_id IN (SELECT job_id FROM demo_jobs);
DELETE FROM derived_representations
WHERE source_id IN (SELECT source_id FROM demo_sources);
DELETE FROM processing_jobs
WHERE id IN (SELECT job_id FROM demo_jobs);
DELETE FROM source_arrivals
WHERE source_id IN (SELECT source_id FROM demo_sources);
DELETE FROM enrollments
WHERE source_id IN (SELECT source_id FROM demo_sources);
DELETE FROM sources
WHERE id IN (SELECT source_id FROM demo_sources);
DELETE FROM canonical_objects
WHERE id IN (SELECT canonical_object_id FROM demo_sources);

COMMIT;
