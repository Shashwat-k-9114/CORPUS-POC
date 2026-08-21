from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class Custodian:
    id: UUID
    slug: str
    name: str
    created_at: datetime


@dataclass(frozen=True)
class Corpus:
    id: UUID
    custodian_id: UUID
    name: str
    kind: str
    created_at: datetime


@dataclass(frozen=True)
class CanonicalObject:
    id: UUID
    custodian_id: UUID
    sha256: str
    byte_size: int
    media_type: str
    storage_key: str
    created_at: datetime


@dataclass(frozen=True)
class Source:
    id: UUID
    custodian_id: UUID
    canonical_object_id: UUID
    display_name: str
    created_at: datetime


@dataclass(frozen=True)
class SourceArrival:
    id: UUID
    source_id: UUID
    claimed_origin: str
    obtained_from: str
    arrival_channel: str
    original_filename: str | None
    received_at: datetime


@dataclass(frozen=True)
class Enrollment:
    id: UUID
    corpus_id: UUID
    source_id: UUID
    enrolled_at: datetime


@dataclass(frozen=True)
class ProcessingJob:
    id: UUID
    source_id: UUID
    pipeline_name: str
    pipeline_version: str
    state: str
    priority: int
    total_pages: int | None
    completed_pages: int
    failed_pages: int
    retry_count: int
    attempt_count: int
    next_attempt_at: datetime | None
    lease_owner: str | None
    lease_acquired_at: datetime | None
    lease_expires_at: datetime | None
    heartbeat_at: datetime | None
    last_error: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class PageCheckpoint:
    id: UUID
    job_id: UUID
    page_number: int
    state: str
    attempt_count: int
    representation_id: UUID | None
    json_representation_id: UUID | None
    render_representation_id: UUID | None
    last_error: str | None
    next_attempt_at: datetime | None
    updated_at: datetime


@dataclass(frozen=True)
class ProcessingAttempt:
    id: UUID
    job_id: UUID
    attempt_number: int
    worker_id: str
    claimed_at: datetime
    heartbeat_at: datetime
    ended_at: datetime | None
    outcome: str | None
    error: str | None


@dataclass(frozen=True)
class WorkerHeartbeat:
    worker_id: str
    started_at: datetime
    last_seen_at: datetime
    status: str
    active_job_id: UUID | None
    updated_at: datetime


@dataclass(frozen=True)
class DerivedRepresentation:
    id: UUID
    source_id: UUID
    custodian_id: UUID
    canonical_object_id: UUID
    canonical_sha256: str
    job_id: UUID
    representation_kind: str
    schema_version: str
    storage_key: str
    content_sha256: str
    byte_size: int
    page_number: int | None
    extractor_name: str
    extractor_version: str
    settings: dict[str, Any]
    settings_digest: str
    created_at: datetime


@dataclass(frozen=True)
class AdmissionReceipt:
    source: Source
    canonical_object: CanonicalObject
    arrival: SourceArrival
    enrollment: Enrollment
    processing_job: ProcessingJob
    exact_duplicate: bool
    idempotent_replay: bool
