"""Repository interfaces and PostgreSQL implementation for foundation records."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Protocol
from uuid import UUID, uuid4

from psycopg.types.json import Jsonb

from app.database import Database
from app.domain.models import (
    AdmissionReceipt,
    CanonicalObject,
    Corpus,
    Custodian,
    DerivedRepresentation,
    Enrollment,
    PageCheckpoint,
    ProcessingAttempt,
    ProcessingJob,
    Source,
    SourceArrival,
    WorkerHeartbeat,
)


class IdempotencyConflict(ValueError):
    """The same idempotency key was reused for a different admission request."""


JOB_FIELDS = "id, source_id, pipeline_name, pipeline_version, state, priority, total_pages, completed_pages, failed_pages, retry_count, attempt_count, next_attempt_at, lease_owner, lease_acquired_at, lease_expires_at, heartbeat_at, last_error, created_at, updated_at"
CHECKPOINT_FIELDS = "id, job_id, page_number, state, attempt_count, representation_id, json_representation_id, render_representation_id, last_error, next_attempt_at, updated_at"
REPRESENTATION_FIELDS = "id, source_id, custodian_id, canonical_object_id, canonical_sha256, job_id, representation_kind, schema_version, storage_key, content_sha256, byte_size, page_number, extractor_name, extractor_version, settings, settings_digest, created_at"


class CustodianRepository(Protocol):
    def list_custodians(self) -> list[Custodian]: ...
    def get_custodian(self, custodian_id: UUID) -> Custodian | None: ...
    def create_custodian(self, slug: str, name: str) -> Custodian: ...
    def create_custodian_with_default_corpus(self, slug: str, name: str) -> tuple[Custodian, Corpus]: ...


class CorpusRepository(Protocol):
    def get_default_for_custodian(self, custodian_id: UUID) -> Corpus | None: ...
    def get_for_custodian(self, corpus_id: UUID, custodian_id: UUID) -> Corpus | None: ...
    def create_default(self, custodian_id: UUID, name: str = "Default corpus") -> Corpus: ...


class SourceRepository(Protocol):
    def get_source(self, source_id: UUID) -> Source | None: ...
    def register(
        self,
        *,
        custodian_id: UUID,
        corpus_id: UUID,
        sha256: str,
        byte_size: int,
        media_type: str,
        storage_key: str,
        display_name: str,
        claimed_origin: str,
        obtained_from: str,
        arrival_channel: str,
        original_filename: str | None,
    ) -> tuple[Source, CanonicalObject, SourceArrival, Enrollment, bool]: ...
    def admit(
        self,
        *,
        custodian_id: UUID,
        corpus_id: UUID,
        sha256: str,
        byte_size: int,
        media_type: str,
        storage_key: str,
        display_name: str,
        claimed_origin: str,
        obtained_from: str,
        arrival_channel: str,
        original_filename: str | None,
        idempotency_key: str | None,
        request_fingerprint: str,
        pipeline_name: str,
        pipeline_version: str,
    ) -> AdmissionReceipt: ...
    def list_sources(
        self, *, custodian_id: UUID, corpus_id: UUID, limit: int, offset: int
    ) -> tuple[list[Source], int]: ...
    def get_source_for_custodian(self, source_id: UUID, custodian_id: UUID) -> Source | None: ...
    def get_canonical_for_source(self, source_id: UUID, custodian_id: UUID) -> CanonicalObject | None: ...
    def list_arrivals(self, source_id: UUID, custodian_id: UUID) -> list[SourceArrival]: ...
    def list_enrollments(self, source_id: UUID, custodian_id: UUID) -> list[Enrollment]: ...


class ProcessingJobRepository(Protocol):
    def create_processing_job(self, source_id: UUID, pipeline_name: str, pipeline_version: str, priority: int = 0) -> ProcessingJob: ...
    def list_processing_jobs(self) -> list[ProcessingJob]: ...
    def list_processing_jobs_for_custodian(self, custodian_id: UUID) -> list[ProcessingJob]: ...
    def list_processing_jobs_page(self, custodian_id: UUID, state: str | None, limit: int, offset: int) -> tuple[list[ProcessingJob], int]: ...
    def get_processing_job(self, job_id: UUID, custodian_id: UUID) -> ProcessingJob | None: ...
    def claim_job(self, worker_id: str, lease_seconds: int) -> ProcessingJob | None: ...
    def heartbeat_job(self, job_id: UUID, worker_id: str, lease_seconds: int) -> None: ...
    def finish_attempt(self, job_id: UUID, worker_id: str, outcome: str, error: str | None = None) -> None: ...
    def recover_expired_jobs(self) -> int: ...
    def retry_job(self, job_id: UUID, custodian_id: UUID) -> ProcessingJob: ...
    def transition_job(self, job_id: UUID, state: str, *, last_error: str | None = None) -> None: ...
    def set_total_pages(self, job_id: UUID, total_pages: int) -> None: ...
    def finalize_job(self, job_id: UUID, worker_id: str) -> ProcessingJob: ...
    def fail_document(self, job_id: UUID, worker_id: str, error: str) -> None: ...
    def list_attempts(self, job_id: UUID, custodian_id: UUID) -> list[ProcessingAttempt]: ...
    def list_worker_heartbeats(self) -> list[WorkerHeartbeat]: ...
    def heartbeat_worker(self, worker_id: str, started_at: datetime, status: str, active_job_id: UUID | None) -> None: ...


class DerivedRepresentationRepository(Protocol):
    def create_representation(self, representation: DerivedRepresentation) -> DerivedRepresentation: ...
    def list_representations(self, source_id: UUID, custodian_id: UUID) -> list[DerivedRepresentation]: ...
    def get_representation(self, representation_id: UUID, custodian_id: UUID) -> DerivedRepresentation | None: ...


class PageCheckpointRepository(Protocol):
    def ensure_page_checkpoints(self, job_id: UUID, page_count: int) -> list[PageCheckpoint]: ...
    def get_page_checkpoint(self, job_id: UUID, page_number: int) -> PageCheckpoint | None: ...
    def list_page_checkpoints(self, job_id: UUID, custodian_id: UUID) -> list[PageCheckpoint]: ...
    def mark_page_processing(self, job_id: UUID, page_number: int, worker_id: str) -> PageCheckpoint: ...
    def mark_page_pending(self, job_id: UUID, page_number: int, error: str) -> None: ...
    def mark_page_failed(self, job_id: UUID, page_number: int, error: str) -> None: ...
    def commit_page_artifacts(self, job_id: UUID, page_number: int, json_representation: DerivedRepresentation, render_representation: DerivedRepresentation) -> None: ...


class PostgresRepositories(
    CustodianRepository,
    CorpusRepository,
    SourceRepository,
    ProcessingJobRepository,
    PageCheckpointRepository,
    DerivedRepresentationRepository,
):
    def __init__(self, database: Database) -> None:
        self.database = database

    def list_custodians(self) -> list[Custodian]:
        with self.database.connection() as connection:
            rows = connection.execute("SELECT id, slug, name, created_at FROM custodians ORDER BY name").fetchall()
        return [_custodian(row) for row in rows]

    def get_custodian(self, custodian_id: UUID) -> Custodian | None:
        with self.database.connection() as connection:
            row = connection.execute("SELECT id, slug, name, created_at FROM custodians WHERE id = %s", (custodian_id,)).fetchone()
        return _custodian(row) if row else None

    def create_custodian(self, slug: str, name: str) -> Custodian:
        custodian_id = uuid4()
        with self.database.connection() as connection:
            row = connection.execute(
                "INSERT INTO custodians (id, slug, name) VALUES (%s, %s, %s) RETURNING id, slug, name, created_at",
                (custodian_id, slug, name),
            ).fetchone()
        return _custodian(row)

    def create_custodian_with_default_corpus(self, slug: str, name: str) -> tuple[Custodian, Corpus]:
        custodian_id = uuid4()
        corpus_id = uuid4()
        with self.database.connection() as connection:
            custodian_row = connection.execute(
                "INSERT INTO custodians (id, slug, name) VALUES (%s, %s, %s) RETURNING id, slug, name, created_at",
                (custodian_id, slug, name),
            ).fetchone()
            corpus_row = connection.execute(
                "INSERT INTO corpora (id, custodian_id, name, kind) VALUES (%s, %s, %s, 'custodian') RETURNING id, custodian_id, name, kind, created_at",
                (corpus_id, custodian_id, "Default corpus"),
            ).fetchone()
        return _custodian(custodian_row), _corpus(corpus_row)

    def get_default_for_custodian(self, custodian_id: UUID) -> Corpus | None:
        with self.database.connection() as connection:
            row = connection.execute(
                "SELECT id, custodian_id, name, kind, created_at FROM corpora WHERE custodian_id = %s AND kind = 'custodian' ORDER BY created_at LIMIT 1",
                (custodian_id,),
            ).fetchone()
        return _corpus(row) if row else None

    def get_for_custodian(self, corpus_id: UUID, custodian_id: UUID) -> Corpus | None:
        with self.database.connection() as connection:
            row = connection.execute(
                "SELECT id, custodian_id, name, kind, created_at FROM corpora WHERE id = %s AND custodian_id = %s",
                (corpus_id, custodian_id),
            ).fetchone()
        return _corpus(row) if row else None

    def create_default(self, custodian_id: UUID, name: str = "Default corpus") -> Corpus:
        with self.database.connection() as connection:
            row = connection.execute(
                "INSERT INTO corpora (id, custodian_id, name, kind) VALUES (%s, %s, %s, 'custodian') ON CONFLICT (custodian_id, kind) DO UPDATE SET name = corpora.name RETURNING id, custodian_id, name, kind, created_at",
                (uuid4(), custodian_id, name),
            ).fetchone()
        return _corpus(row)

    def register(
        self,
        *,
        custodian_id: UUID,
        corpus_id: UUID,
        sha256: str,
        byte_size: int,
        media_type: str,
        storage_key: str,
        display_name: str,
        claimed_origin: str,
        obtained_from: str,
        arrival_channel: str,
        original_filename: str | None,
    ) -> tuple[Source, CanonicalObject, SourceArrival, Enrollment, bool]:
        now = datetime.now(timezone.utc)
        source_id = uuid4()
        object_id = uuid4()
        arrival_id = uuid4()
        enrollment_id = uuid4()
        with self.database.connection() as connection:
            valid_corpus = connection.execute(
                "SELECT 1 FROM corpora WHERE id = %s AND custodian_id = %s",
                (corpus_id, custodian_id),
            ).fetchone()
            if not valid_corpus:
                raise ValueError("The corpus does not belong to the supplied custodian.")
            object_row = connection.execute(
                "INSERT INTO canonical_objects (id, custodian_id, sha256, byte_size, media_type, storage_key) VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (custodian_id, sha256) DO UPDATE SET sha256 = EXCLUDED.sha256 RETURNING id, custodian_id, sha256, byte_size, media_type, storage_key, created_at",
                (object_id, custodian_id, sha256, byte_size, media_type, storage_key),
            ).fetchone()
            existing_source = connection.execute(
                "SELECT id, custodian_id, canonical_object_id, display_name, created_at FROM sources WHERE custodian_id = %s AND canonical_object_id = %s",
                (custodian_id, object_row["id"]),
            ).fetchone()
            duplicate = existing_source is not None
            source_row = existing_source or connection.execute(
                "INSERT INTO sources (id, custodian_id, canonical_object_id, display_name) VALUES (%s, %s, %s, %s) RETURNING id, custodian_id, canonical_object_id, display_name, created_at",
                (source_id, custodian_id, object_row["id"], display_name),
            ).fetchone()
            arrival_row = connection.execute(
                "INSERT INTO source_arrivals (id, source_id, claimed_origin, obtained_from, arrival_channel, original_filename, received_at) VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id, source_id, claimed_origin, obtained_from, arrival_channel, original_filename, received_at",
                (arrival_id, source_row["id"], claimed_origin, obtained_from, arrival_channel, original_filename, now),
            ).fetchone()
            enrollment_row = connection.execute(
                "INSERT INTO enrollments (id, corpus_id, source_id) VALUES (%s, %s, %s) ON CONFLICT (corpus_id, source_id) DO UPDATE SET source_id = EXCLUDED.source_id RETURNING id, corpus_id, source_id, enrolled_at",
                (enrollment_id, corpus_id, source_row["id"]),
            ).fetchone()
        return _source(source_row), _canonical(object_row), _arrival(arrival_row), _enrollment(enrollment_row), duplicate

    def admit(
        self,
        *,
        custodian_id: UUID,
        corpus_id: UUID,
        sha256: str,
        byte_size: int,
        media_type: str,
        storage_key: str,
        display_name: str,
        claimed_origin: str,
        obtained_from: str,
        arrival_channel: str,
        original_filename: str | None,
        idempotency_key: str | None,
        request_fingerprint: str,
        pipeline_name: str,
        pipeline_version: str,
    ) -> AdmissionReceipt:
        """Admit one canonical object and all durable admission records atomically."""
        now = datetime.now(timezone.utc)
        with self.database.connection() as connection:
            connection.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
                (f"{custodian_id}:{sha256}",),
            )
            if idempotency_key:
                connection.execute(
                    "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
                    (f"{custodian_id}:{idempotency_key}",),
                )
                prior = connection.execute(
                    "SELECT source_id, canonical_object_id, arrival_id, enrollment_id, processing_job_id, exact_duplicate, request_fingerprint FROM admission_requests WHERE custodian_id = %s AND idempotency_key = %s",
                    (custodian_id, idempotency_key),
                ).fetchone()
                if prior:
                    if prior["request_fingerprint"] != request_fingerprint:
                        raise IdempotencyConflict("Idempotency-Key was already used for a different request.")
                    return _load_admission(
                        connection,
                        source_id=prior["source_id"],
                        canonical_object_id=prior["canonical_object_id"],
                        arrival_id=prior["arrival_id"],
                        enrollment_id=prior["enrollment_id"],
                        processing_job_id=prior["processing_job_id"],
                        exact_duplicate=prior["exact_duplicate"],
                        idempotent_replay=True,
                    )

            valid_custodian = connection.execute(
                "SELECT 1 FROM custodians WHERE id = %s", (custodian_id,)
            ).fetchone()
            if not valid_custodian:
                raise ValueError("The custodian does not exist.")
            valid_corpus = connection.execute(
                "SELECT 1 FROM corpora WHERE id = %s AND custodian_id = %s",
                (corpus_id, custodian_id),
            ).fetchone()
            if not valid_corpus:
                raise ValueError("The corpus does not belong to the supplied custodian.")

            object_row = connection.execute(
                "INSERT INTO canonical_objects (id, custodian_id, sha256, byte_size, media_type, storage_key) VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (custodian_id, sha256) DO UPDATE SET sha256 = EXCLUDED.sha256 RETURNING id, custodian_id, sha256, byte_size, media_type, storage_key, created_at",
                (uuid4(), custodian_id, sha256, byte_size, media_type, storage_key),
            ).fetchone()
            existing_source = connection.execute(
                "SELECT id, custodian_id, canonical_object_id, display_name, created_at FROM sources WHERE custodian_id = %s AND canonical_object_id = %s",
                (custodian_id, object_row["id"]),
            ).fetchone()
            exact_duplicate = existing_source is not None
            source_row = existing_source or connection.execute(
                "INSERT INTO sources (id, custodian_id, canonical_object_id, display_name) VALUES (%s, %s, %s, %s) RETURNING id, custodian_id, canonical_object_id, display_name, created_at",
                (uuid4(), custodian_id, object_row["id"], display_name),
            ).fetchone()
            arrival_row = connection.execute(
                "INSERT INTO source_arrivals (id, source_id, claimed_origin, obtained_from, arrival_channel, original_filename, received_at) VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id, source_id, claimed_origin, obtained_from, arrival_channel, original_filename, received_at",
                (uuid4(), source_row["id"], claimed_origin, obtained_from, arrival_channel, original_filename, now),
            ).fetchone()
            enrollment_row = connection.execute(
                "INSERT INTO enrollments (id, corpus_id, source_id) VALUES (%s, %s, %s) ON CONFLICT (corpus_id, source_id) DO UPDATE SET source_id = EXCLUDED.source_id RETURNING id, corpus_id, source_id, enrolled_at",
                (uuid4(), corpus_id, source_row["id"]),
            ).fetchone()
            # Exact duplicate deliveries preserve the source's existing pipeline
            # identity, including after completion. A repeat arrival must not create
            # a redundant active job for bytes already admitted and processed.
            job_row = connection.execute(
                f"SELECT {JOB_FIELDS} FROM processing_jobs WHERE source_id = %s ORDER BY CASE state WHEN 'processing' THEN 0 WHEN 'queued' THEN 1 WHEN 'partial' THEN 2 WHEN 'failed' THEN 3 WHEN 'completed' THEN 4 ELSE 5 END, created_at DESC, id DESC LIMIT 1 FOR UPDATE",
                (source_row["id"],),
            ).fetchone()
            if job_row is None:
                job_row = connection.execute(
                    f"INSERT INTO processing_jobs (id, source_id, pipeline_name, pipeline_version, state, priority) VALUES (%s, %s, %s, %s, 'queued', 0) RETURNING {JOB_FIELDS}",
                    (uuid4(), source_row["id"], pipeline_name, pipeline_version),
                ).fetchone()

            if idempotency_key:
                connection.execute(
                    "INSERT INTO admission_requests (id, custodian_id, idempotency_key, request_fingerprint, source_id, canonical_object_id, arrival_id, enrollment_id, processing_job_id, exact_duplicate) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    (uuid4(), custodian_id, idempotency_key, request_fingerprint, source_row["id"], object_row["id"], arrival_row["id"], enrollment_row["id"], job_row["id"], exact_duplicate),
                )
            return AdmissionReceipt(
                source=_source(source_row),
                canonical_object=_canonical(object_row),
                arrival=_arrival(arrival_row),
                enrollment=_enrollment(enrollment_row),
                processing_job=_job(job_row),
                exact_duplicate=exact_duplicate,
                idempotent_replay=False,
            )

    def get_source(self, source_id: UUID) -> Source | None:
        with self.database.connection() as connection:
            row = connection.execute(
                "SELECT id, custodian_id, canonical_object_id, display_name, created_at FROM sources WHERE id = %s",
                (source_id,),
            ).fetchone()
        return _source(row) if row else None

    def get_source_for_custodian(self, source_id: UUID, custodian_id: UUID) -> Source | None:
        with self.database.connection() as connection:
            row = connection.execute(
                "SELECT id, custodian_id, canonical_object_id, display_name, created_at FROM sources WHERE id = %s AND custodian_id = %s",
                (source_id, custodian_id),
            ).fetchone()
        return _source(row) if row else None

    def get_canonical_for_source(self, source_id: UUID, custodian_id: UUID) -> CanonicalObject | None:
        with self.database.connection() as connection:
            row = connection.execute(
                "SELECT c.id, c.custodian_id, c.sha256, c.byte_size, c.media_type, c.storage_key, c.created_at FROM canonical_objects c JOIN sources s ON s.canonical_object_id = c.id WHERE s.id = %s AND s.custodian_id = %s",
                (source_id, custodian_id),
            ).fetchone()
        return _canonical(row) if row else None

    def list_sources(
        self, *, custodian_id: UUID, corpus_id: UUID, limit: int, offset: int
    ) -> tuple[list[Source], int]:
        with self.database.connection() as connection:
            valid_corpus = connection.execute(
                "SELECT 1 FROM corpora WHERE id = %s AND custodian_id = %s",
                (corpus_id, custodian_id),
            ).fetchone()
            if not valid_corpus:
                raise ValueError("The corpus does not belong to the supplied custodian.")
            count_row = connection.execute(
                "SELECT count(*) AS total FROM sources s JOIN enrollments e ON e.source_id = s.id WHERE s.custodian_id = %s AND e.corpus_id = %s",
                (custodian_id, corpus_id),
            ).fetchone()
            rows = connection.execute(
                "SELECT s.id, s.custodian_id, s.canonical_object_id, s.display_name, s.created_at FROM sources s JOIN enrollments e ON e.source_id = s.id WHERE s.custodian_id = %s AND e.corpus_id = %s ORDER BY s.created_at, s.id LIMIT %s OFFSET %s",
                (custodian_id, corpus_id, limit, offset),
            ).fetchall()
        return [_source(row) for row in rows], int(count_row["total"])

    def list_arrivals(self, source_id: UUID, custodian_id: UUID) -> list[SourceArrival]:
        with self.database.connection() as connection:
            rows = connection.execute(
                "SELECT a.id, a.source_id, a.claimed_origin, a.obtained_from, a.arrival_channel, a.original_filename, a.received_at FROM source_arrivals a JOIN sources s ON s.id = a.source_id WHERE a.source_id = %s AND s.custodian_id = %s ORDER BY a.received_at, a.id",
                (source_id, custodian_id),
            ).fetchall()
        return [_arrival(row) for row in rows]

    def list_enrollments(self, source_id: UUID, custodian_id: UUID) -> list[Enrollment]:
        with self.database.connection() as connection:
            rows = connection.execute(
                "SELECT e.id, e.corpus_id, e.source_id, e.enrolled_at FROM enrollments e JOIN sources s ON s.id = e.source_id JOIN corpora c ON c.id = e.corpus_id WHERE e.source_id = %s AND s.custodian_id = %s AND c.custodian_id = %s ORDER BY e.enrolled_at, e.id",
                (source_id, custodian_id, custodian_id),
            ).fetchall()
        return [_enrollment(row) for row in rows]

    def create_processing_job(self, source_id: UUID, pipeline_name: str, pipeline_version: str, priority: int = 0) -> ProcessingJob:
        job_id = uuid4()
        with self.database.connection() as connection:
            row = connection.execute(
                f"INSERT INTO processing_jobs (id, source_id, pipeline_name, pipeline_version, state, priority) VALUES (%s, %s, %s, %s, 'queued', %s) RETURNING {JOB_FIELDS}",
                (job_id, source_id, pipeline_name, pipeline_version, priority),
            ).fetchone()
        return _job(row)

    def list_processing_jobs(self) -> list[ProcessingJob]:
        with self.database.connection() as connection:
            rows = connection.execute(f"SELECT {JOB_FIELDS} FROM processing_jobs ORDER BY created_at DESC").fetchall()
        return [_job(row) for row in rows]

    def list_processing_jobs_for_custodian(self, custodian_id: UUID) -> list[ProcessingJob]:
        with self.database.connection() as connection:
            rows = connection.execute(
                f"SELECT j.{JOB_FIELDS.replace(', ', ', j.')} FROM processing_jobs j JOIN sources s ON s.id = j.source_id WHERE s.custodian_id = %s ORDER BY j.created_at DESC, j.id DESC",
                (custodian_id,),
            ).fetchall()
        return [_job(row) for row in rows]

    def list_processing_jobs_page(self, custodian_id: UUID, state: str | None, limit: int, offset: int) -> tuple[list[ProcessingJob], int]:
        with self.database.connection() as connection:
            params: list[Any] = [custodian_id]
            state_clause = ""
            if state:
                state_clause = " AND j.state = %s"
                params.append(state)
            count_row = connection.execute(
                f"SELECT count(*) AS total FROM processing_jobs j JOIN sources s ON s.id = j.source_id WHERE s.custodian_id = %s{state_clause}",
                params,
            ).fetchone()
            params.extend([limit, offset])
            rows = connection.execute(
                f"SELECT j.{JOB_FIELDS.replace(', ', ', j.')} FROM processing_jobs j JOIN sources s ON s.id = j.source_id WHERE s.custodian_id = %s{state_clause} ORDER BY j.priority DESC, j.created_at DESC, j.id DESC LIMIT %s OFFSET %s",
                params,
            ).fetchall()
        return [_job(row) for row in rows], int(count_row["total"])

    def get_processing_job(self, job_id: UUID, custodian_id: UUID) -> ProcessingJob | None:
        with self.database.connection() as connection:
            row = connection.execute(
                f"SELECT j.{JOB_FIELDS.replace(', ', ', j.')} FROM processing_jobs j JOIN sources s ON s.id = j.source_id WHERE j.id = %s AND s.custodian_id = %s",
                (job_id, custodian_id),
            ).fetchone()
        return _job(row) if row else None

    def claim_job(self, worker_id: str, lease_seconds: int) -> ProcessingJob | None:
        self.recover_expired_jobs()
        with self.database.connection() as connection:
            row = connection.execute(
                f"""
                WITH candidate AS (
                    SELECT id FROM processing_jobs
                    WHERE state = 'queued'
                      AND (next_attempt_at IS NULL OR next_attempt_at <= now())
                    ORDER BY priority DESC, created_at, id
                    FOR UPDATE SKIP LOCKED
                    LIMIT 1
                )
                UPDATE processing_jobs AS jobs
                SET state = 'processing',
                    lease_owner = %s,
                    lease_acquired_at = now(),
                    heartbeat_at = now(),
                    lease_expires_at = now() + (%s * interval '1 second'),
                    attempt_count = jobs.attempt_count + 1,
                    updated_at = now()
                FROM candidate
                WHERE jobs.id = candidate.id
                 RETURNING jobs.{JOB_FIELDS.replace(', ', ', jobs.')}
                """,
                (worker_id, lease_seconds),
            ).fetchone()
            if row is None:
                return None
            connection.execute(
                "INSERT INTO processing_attempts (id, job_id, attempt_number, worker_id, claimed_at, heartbeat_at) VALUES (%s, %s, %s, %s, now(), now())",
                (uuid4(), row["id"], row["attempt_count"], worker_id),
            )
        return _job(row)

    def heartbeat_job(self, job_id: UUID, worker_id: str, lease_seconds: int) -> None:
        with self.database.connection() as connection:
            connection.execute(
                "UPDATE processing_jobs SET heartbeat_at = now(), lease_expires_at = now() + (%s * interval '1 second'), updated_at = now() WHERE id = %s AND state = 'processing' AND lease_owner = %s",
                (lease_seconds, job_id, worker_id),
            )
            connection.execute(
                "UPDATE processing_attempts SET heartbeat_at = now() WHERE job_id = %s AND worker_id = %s AND ended_at IS NULL",
                (job_id, worker_id),
            )

    def finish_attempt(self, job_id: UUID, worker_id: str, outcome: str, error: str | None = None) -> None:
        with self.database.connection() as connection:
            connection.execute(
                "UPDATE processing_attempts SET ended_at = now(), outcome = %s, error = %s, heartbeat_at = now() WHERE job_id = %s AND worker_id = %s AND ended_at IS NULL",
                (outcome, error, job_id, worker_id),
            )

    def recover_expired_jobs(self) -> int:
        with self.database.connection() as connection:
            rows = connection.execute(
                "UPDATE processing_jobs SET state = 'queued', lease_owner = NULL, lease_acquired_at = NULL, lease_expires_at = NULL, heartbeat_at = NULL, next_attempt_at = now(), updated_at = now() WHERE state = 'processing' AND lease_expires_at IS NOT NULL AND lease_expires_at < now() RETURNING id"
            ).fetchall()
            for row in rows:
                connection.execute(
                    "UPDATE page_checkpoints SET state = 'pending', next_attempt_at = now(), updated_at = now() WHERE job_id = %s AND state = 'processing'",
                    (row["id"],),
                )
                connection.execute(
                    "UPDATE processing_attempts SET ended_at = now(), outcome = 'interrupted', error = COALESCE(error, 'Lease expired before completion') WHERE job_id = %s AND ended_at IS NULL",
                    (row["id"],),
                )
        return len(rows)

    def transition_job(self, job_id: UUID, state: str, *, last_error: str | None = None) -> None:
        allowed = {
            "queued": {"processing"},
            "processing": {"queued", "completed", "partial", "failed"},
            "partial": {"queued"},
            "failed": {"queued"},
            "completed": set(),
        }
        with self.database.connection() as connection:
            row = connection.execute("SELECT state FROM processing_jobs WHERE id = %s FOR UPDATE", (job_id,)).fetchone()
            if row is None:
                raise ValueError("Processing job not found.")
            if state not in allowed[row["state"]]:
                raise ValueError(f"Invalid processing job transition: {row['state']} -> {state}.")
            connection.execute(
                "UPDATE processing_jobs SET state = %s, last_error = %s, updated_at = now(), lease_owner = CASE WHEN %s <> 'processing' THEN NULL ELSE lease_owner END, lease_expires_at = CASE WHEN %s <> 'processing' THEN NULL ELSE lease_expires_at END WHERE id = %s",
                (state, last_error, state, state, job_id),
            )

    def set_total_pages(self, job_id: UUID, total_pages: int) -> None:
        with self.database.connection() as connection:
            connection.execute(
                "UPDATE processing_jobs SET total_pages = %s, updated_at = now() WHERE id = %s AND state = 'processing'",
                (total_pages, job_id),
            )

    def finalize_job(self, job_id: UUID, worker_id: str) -> ProcessingJob:
        with self.database.connection() as connection:
            row = connection.execute(
                f"SELECT {JOB_FIELDS} FROM processing_jobs WHERE id = %s AND lease_owner = %s FOR UPDATE",
                (job_id, worker_id),
            ).fetchone()
            if row is None:
                raise ValueError("Processing lease is no longer held by this worker.")
            counts = connection.execute(
                "SELECT count(*) FILTER (WHERE state = 'completed') AS completed, count(*) FILTER (WHERE state = 'failed') AS failed FROM page_checkpoints WHERE job_id = %s",
                (job_id,),
            ).fetchone()
            completed = int(counts["completed"])
            failed = int(counts["failed"])
            total = int(row["total_pages"] or 0)
            if failed and completed:
                state = "partial"
            elif failed and not completed:
                state = "failed"
            elif total == completed:
                state = "completed"
            else:
                state = "processing"
            updated = connection.execute(
                f"UPDATE processing_jobs SET state = %s, completed_pages = %s, failed_pages = %s, lease_owner = NULL, lease_acquired_at = NULL, lease_expires_at = NULL, heartbeat_at = NULL, updated_at = now() WHERE id = %s RETURNING {JOB_FIELDS}",
                (state, completed, failed, job_id),
            ).fetchone()
            connection.execute(
                "UPDATE processing_attempts SET ended_at = now(), outcome = %s WHERE job_id = %s AND worker_id = %s AND ended_at IS NULL",
                (state, job_id, worker_id),
            )
        return _job(updated)

    def fail_document(self, job_id: UUID, worker_id: str, error: str) -> None:
        with self.database.connection() as connection:
            row = connection.execute(
                "UPDATE processing_jobs SET state = 'failed', last_error = %s, lease_owner = NULL, lease_acquired_at = NULL, lease_expires_at = NULL, heartbeat_at = NULL, updated_at = now() WHERE id = %s AND state = 'processing' AND lease_owner = %s RETURNING id",
                (error, job_id, worker_id),
            ).fetchone()
            if row:
                connection.execute(
                    "UPDATE processing_attempts SET ended_at = now(), outcome = 'failed', error = %s WHERE job_id = %s AND worker_id = %s AND ended_at IS NULL",
                    (error, job_id, worker_id),
                )

    def retry_job(self, job_id: UUID, custodian_id: UUID) -> ProcessingJob:
        with self.database.connection() as connection:
            row = connection.execute(
                f"SELECT j.{JOB_FIELDS.replace(', ', ', j.')} FROM processing_jobs j JOIN sources s ON s.id = j.source_id WHERE j.id = %s AND s.custodian_id = %s FOR UPDATE",
                (job_id, custodian_id),
            ).fetchone()
            if row is None:
                raise ValueError("Processing job not found.")
            if row["state"] not in {"partial", "failed"}:
                raise ValueError("Only partial or failed jobs can be retried.")
            updated = connection.execute(
                f"UPDATE processing_jobs SET state = 'queued', retry_count = retry_count + 1, next_attempt_at = now(), lease_owner = NULL, lease_acquired_at = NULL, lease_expires_at = NULL, heartbeat_at = NULL, updated_at = now() WHERE id = %s RETURNING {JOB_FIELDS}",
                (job_id,),
            ).fetchone()
            connection.execute(
                "UPDATE page_checkpoints SET state = 'pending', next_attempt_at = now(), representation_id = NULL, json_representation_id = NULL, render_representation_id = NULL, updated_at = now() WHERE job_id = %s AND state = 'failed'",
                (job_id,),
            )
        return _job(updated)

    def list_attempts(self, job_id: UUID, custodian_id: UUID) -> list[ProcessingAttempt]:
        with self.database.connection() as connection:
            rows = connection.execute(
                "SELECT a.id, a.job_id, a.attempt_number, a.worker_id, a.claimed_at, a.heartbeat_at, a.ended_at, a.outcome, a.error FROM processing_attempts a JOIN processing_jobs j ON j.id = a.job_id JOIN sources s ON s.id = j.source_id WHERE a.job_id = %s AND s.custodian_id = %s ORDER BY a.attempt_number",
                (job_id, custodian_id),
            ).fetchall()
        return [_attempt(row) for row in rows]

    def heartbeat_worker(self, worker_id: str, started_at: datetime, status: str, active_job_id: UUID | None) -> None:
        with self.database.connection() as connection:
            connection.execute(
                "INSERT INTO worker_heartbeats (worker_id, started_at, last_seen_at, status, active_job_id, updated_at) VALUES (%s, %s, now(), %s, %s, now()) ON CONFLICT (worker_id) DO UPDATE SET last_seen_at = now(), status = EXCLUDED.status, active_job_id = EXCLUDED.active_job_id, updated_at = now()",
                (worker_id, started_at, status, active_job_id),
            )

    def list_worker_heartbeats(self) -> list[WorkerHeartbeat]:
        with self.database.connection() as connection:
            rows = connection.execute(
                "SELECT worker_id, started_at, last_seen_at, status, active_job_id, updated_at FROM worker_heartbeats ORDER BY worker_id"
            ).fetchall()
        return [_worker_heartbeat(row) for row in rows]

    def ensure_page_checkpoints(self, job_id: UUID, page_count: int) -> list[PageCheckpoint]:
        if page_count < 0:
            raise ValueError("page_count must be zero or greater.")
        with self.database.connection() as connection:
            for page_number in range(1, page_count + 1):
                connection.execute(
                    "INSERT INTO page_checkpoints (id, job_id, page_number, state) VALUES (%s, %s, %s, 'pending') ON CONFLICT (job_id, page_number) DO NOTHING",
                    (uuid4(), job_id, page_number),
                )
            rows = connection.execute(
                f"SELECT {CHECKPOINT_FIELDS} FROM page_checkpoints WHERE job_id = %s ORDER BY page_number",
                (job_id,),
            ).fetchall()
        return [_checkpoint(row) for row in rows]

    def get_page_checkpoint(self, job_id: UUID, page_number: int) -> PageCheckpoint | None:
        with self.database.connection() as connection:
            row = connection.execute(
                f"SELECT {CHECKPOINT_FIELDS} FROM page_checkpoints WHERE job_id = %s AND page_number = %s",
                (job_id, page_number),
            ).fetchone()
        return _checkpoint(row) if row else None

    def list_page_checkpoints(self, job_id: UUID, custodian_id: UUID) -> list[PageCheckpoint]:
        with self.database.connection() as connection:
            rows = connection.execute(
                f"SELECT pc.{CHECKPOINT_FIELDS.replace(', ', ', pc.')} FROM page_checkpoints pc JOIN processing_jobs j ON j.id = pc.job_id JOIN sources s ON s.id = j.source_id WHERE pc.job_id = %s AND s.custodian_id = %s ORDER BY pc.page_number",
                (job_id, custodian_id),
            ).fetchall()
        return [_checkpoint(row) for row in rows]

    def mark_page_processing(self, job_id: UUID, page_number: int, worker_id: str) -> PageCheckpoint:
        with self.database.connection() as connection:
            row = connection.execute(
                f"UPDATE page_checkpoints SET state = 'processing', attempt_count = attempt_count + 1, updated_at = now() WHERE job_id = %s AND page_number = %s AND state IN ('pending', 'queued') AND EXISTS (SELECT 1 FROM processing_jobs WHERE id = %s AND state = 'processing' AND lease_owner = %s) RETURNING {CHECKPOINT_FIELDS}",
                (job_id, page_number, job_id, worker_id),
            ).fetchone()
            if row is None:
                existing = connection.execute(
                    f"SELECT {CHECKPOINT_FIELDS} FROM page_checkpoints WHERE job_id = %s AND page_number = %s",
                    (job_id, page_number),
                ).fetchone()
                if existing is None:
                    raise ValueError("Page checkpoint not found.")
                return _checkpoint(existing)
        return _checkpoint(row)

    def mark_page_pending(self, job_id: UUID, page_number: int, error: str) -> None:
        with self.database.connection() as connection:
            connection.execute(
                "UPDATE page_checkpoints SET state = 'pending', last_error = %s, next_attempt_at = now(), updated_at = now() WHERE job_id = %s AND page_number = %s AND state = 'processing'",
                (error, job_id, page_number),
            )

    def mark_page_failed(self, job_id: UUID, page_number: int, error: str) -> None:
        with self.database.connection() as connection:
            connection.execute(
                "UPDATE page_checkpoints SET state = 'failed', last_error = %s, next_attempt_at = NULL, updated_at = now() WHERE job_id = %s AND page_number = %s AND state = 'processing'",
                (error, job_id, page_number),
            )

    def commit_page_artifacts(
        self,
        job_id: UUID,
        page_number: int,
        json_representation: DerivedRepresentation,
        render_representation: DerivedRepresentation,
    ) -> None:
        with self.database.connection() as connection:
            for representation in (json_representation, render_representation):
                connection.execute(
                    "INSERT INTO derived_representations (id, source_id, custodian_id, canonical_object_id, canonical_sha256, job_id, representation_kind, schema_version, storage_key, content_sha256, byte_size, page_number, extractor_name, extractor_version, settings, settings_digest) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT (job_id, representation_kind, page_number) DO NOTHING",
                    (representation.id, representation.source_id, representation.custodian_id, representation.canonical_object_id, representation.canonical_sha256, representation.job_id, representation.representation_kind, representation.schema_version, representation.storage_key, representation.content_sha256, representation.byte_size, representation.page_number, representation.extractor_name, representation.extractor_version, Jsonb(representation.settings), representation.settings_digest),
                )
            rows = connection.execute(
                "SELECT id, representation_kind FROM derived_representations WHERE job_id = %s AND page_number = %s AND representation_kind IN ('page-json', 'page-render')",
                (job_id, page_number),
            ).fetchall()
            ids = {row["representation_kind"]: row["id"] for row in rows}
            if not {"page-json", "page-render"}.issubset(ids):
                raise RuntimeError("Page artifacts were not persisted.")
            connection.execute(
                "UPDATE page_checkpoints SET state = 'completed', representation_id = %s, json_representation_id = %s, render_representation_id = %s, last_error = NULL, next_attempt_at = NULL, updated_at = now() WHERE job_id = %s AND page_number = %s",
                (ids["page-json"], ids["page-json"], ids["page-render"], job_id, page_number),
            )

    def create_representation(self, representation: DerivedRepresentation) -> DerivedRepresentation:
        with self.database.connection() as connection:
            row = connection.execute(
                f"INSERT INTO derived_representations (id, source_id, custodian_id, canonical_object_id, canonical_sha256, job_id, representation_kind, schema_version, storage_key, content_sha256, byte_size, page_number, extractor_name, extractor_version, settings, settings_digest) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING {REPRESENTATION_FIELDS}",
                (representation.id, representation.source_id, representation.custodian_id, representation.canonical_object_id, representation.canonical_sha256, representation.job_id, representation.representation_kind, representation.schema_version, representation.storage_key, representation.content_sha256, representation.byte_size, representation.page_number, representation.extractor_name, representation.extractor_version, Jsonb(representation.settings), representation.settings_digest),
            ).fetchone()
        return _representation(row)

    def list_representations(self, source_id: UUID, custodian_id: UUID) -> list[DerivedRepresentation]:
        with self.database.connection() as connection:
            rows = connection.execute(
                f"SELECT d.{REPRESENTATION_FIELDS.replace(', ', ', d.')} FROM derived_representations d WHERE d.source_id = %s AND d.custodian_id = %s ORDER BY d.page_number, d.representation_kind, d.created_at, d.id",
                (source_id, custodian_id),
            ).fetchall()
        return [_representation(row) for row in rows]

    def get_representation(self, representation_id: UUID, custodian_id: UUID) -> DerivedRepresentation | None:
        with self.database.connection() as connection:
            row = connection.execute(
                f"SELECT d.{REPRESENTATION_FIELDS.replace(', ', ', d.')} FROM derived_representations d WHERE d.id = %s AND d.custodian_id = %s",
                (representation_id, custodian_id),
            ).fetchone()
        return _representation(row) if row else None


def _custodian(row: dict[str, Any]) -> Custodian:
    return Custodian(**row)


def _corpus(row: dict[str, Any]) -> Corpus:
    return Corpus(**row)


def _canonical(row: dict[str, Any]) -> CanonicalObject:
    return CanonicalObject(**row)


def _source(row: dict[str, Any]) -> Source:
    return Source(**row)


def _arrival(row: dict[str, Any]) -> SourceArrival:
    return SourceArrival(**row)


def _enrollment(row: dict[str, Any]) -> Enrollment:
    return Enrollment(**row)


def _job(row: dict[str, Any]) -> ProcessingJob:
    return ProcessingJob(**row)


def _checkpoint(row: dict[str, Any]) -> PageCheckpoint:
    return PageCheckpoint(**row)


def _attempt(row: dict[str, Any]) -> ProcessingAttempt:
    return ProcessingAttempt(**row)


def _worker_heartbeat(row: dict[str, Any]) -> WorkerHeartbeat:
    return WorkerHeartbeat(**row)


def _representation(row: dict[str, Any]) -> DerivedRepresentation:
    return DerivedRepresentation(**row)


def _load_admission(
    connection: Any,
    *,
    source_id: UUID,
    canonical_object_id: UUID,
    arrival_id: UUID,
    enrollment_id: UUID,
    processing_job_id: UUID,
    exact_duplicate: bool,
    idempotent_replay: bool,
) -> AdmissionReceipt:
    source_row = connection.execute(
        "SELECT id, custodian_id, canonical_object_id, display_name, created_at FROM sources WHERE id = %s",
        (source_id,),
    ).fetchone()
    canonical_row = connection.execute(
        "SELECT id, custodian_id, sha256, byte_size, media_type, storage_key, created_at FROM canonical_objects WHERE id = %s",
        (canonical_object_id,),
    ).fetchone()
    arrival_row = connection.execute(
        "SELECT id, source_id, claimed_origin, obtained_from, arrival_channel, original_filename, received_at FROM source_arrivals WHERE id = %s",
        (arrival_id,),
    ).fetchone()
    enrollment_row = connection.execute(
        "SELECT id, corpus_id, source_id, enrolled_at FROM enrollments WHERE id = %s",
        (enrollment_id,),
    ).fetchone()
    job_row = connection.execute(
        f"SELECT {JOB_FIELDS} FROM processing_jobs WHERE id = %s",
        (processing_job_id,),
    ).fetchone()
    if not all((source_row, canonical_row, arrival_row, enrollment_row, job_row)):
        raise RuntimeError("The idempotent admission record references missing data.")
    return AdmissionReceipt(
        source=_source(source_row),
        canonical_object=_canonical(canonical_row),
        arrival=_arrival(arrival_row),
        enrollment=_enrollment(enrollment_row),
        processing_job=_job(job_row),
        exact_duplicate=exact_duplicate,
        idempotent_replay=idempotent_replay,
    )
