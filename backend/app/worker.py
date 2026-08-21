"""Separate durable PDF processor process."""

from __future__ import annotations

import hashlib
import logging
import os
import signal
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from app.blobstore import BlobStore, create_blob_store
from app.config import Settings
from app.database import Database
from app.domain.models import DerivedRepresentation, ProcessingJob
from app.processor import DocumentProcessingError, PageProcessingError, open_pdf, process_page
from app.repositories import PostgresRepositories

logger = logging.getLogger("corpus.worker")


@dataclass
class LeaseHeartbeat:
    repositories: PostgresRepositories
    job_id: UUID
    worker_id: str
    lease_seconds: int
    stop_event: threading.Event

    def run(self) -> None:
        interval = max(1.0, self.lease_seconds / 3)
        while not self.stop_event.wait(interval):
            try:
                self.repositories.heartbeat_job(self.job_id, self.worker_id, self.lease_seconds)
            except Exception:
                logger.exception("Lease heartbeat failed for job %s", self.job_id)


def run_forever(settings: Settings, stop_event: threading.Event | None = None, worker_id: str | None = None) -> None:
    stop_event = stop_event or threading.Event()
    worker_id = worker_id or f"worker-{os.getpid()}-{uuid4().hex[:8]}"
    repositories = PostgresRepositories(Database(settings.database_url))
    started_at = datetime.now(timezone.utc)
    _install_signal_handlers(stop_event)
    logger.info("Durable Corpus worker %s started", worker_id)
    while not stop_event.is_set():
        try:
            repositories.heartbeat_worker(worker_id, started_at, "idle", None)
            job = repositories.claim_job(worker_id, settings.worker_lease_seconds)
            if job is None:
                stop_event.wait(settings.worker_poll_seconds)
                continue
            repositories.heartbeat_worker(worker_id, started_at, "processing", job.id)
            process_claimed_job(settings, repositories, job, worker_id, stop_event)
        except Exception:
            logger.exception("Worker loop failure")
            stop_event.wait(settings.worker_poll_seconds)
    repositories.heartbeat_worker(worker_id, started_at, "stopped", None)
    logger.info("Durable Corpus worker %s stopped", worker_id)


def process_claimed_job(settings: Settings, repositories: PostgresRepositories, job: ProcessingJob, worker_id: str, stop_event: threading.Event) -> None:
    source = repositories.get_source(job.source_id)
    if source is None:
        repositories.fail_document(job.id, worker_id, "Source record is missing.")
        return
    canonical = repositories.get_canonical_for_source(source.id, source.custodian_id)
    if canonical is None:
        repositories.fail_document(job.id, worker_id, "Canonical object record is missing.")
        return
    settings_digest = _settings_digest(settings)
    blob_store = create_blob_store(settings)
    heartbeat_stop = threading.Event()
    heartbeat = threading.Thread(
        target=LeaseHeartbeat(repositories, job.id, worker_id, settings.worker_lease_seconds, heartbeat_stop).run,
        name=f"lease-heartbeat-{job.id}",
        daemon=True,
    )
    heartbeat.start()
    try:
        with blob_store.open(canonical.storage_key) as canonical_stream:
            actual_hash = _hash_stream(canonical_stream)
            if actual_hash != canonical.sha256:
                repositories.fail_document(job.id, worker_id, "Canonical SHA-256 does not match metadata.")
                return
            canonical_stream.seek(0)
            try:
                with open_pdf(canonical_stream) as pdf:
                    total_pages = len(pdf.pages)
                    repositories.set_total_pages(job.id, total_pages)
                    repositories.ensure_page_checkpoints(job.id, total_pages)
                    _process_pages(settings, repositories, blob_store, job, source.custodian_id, source.id, canonical.id, canonical.sha256, settings_digest, pdf, worker_id, stop_event)
            except DocumentProcessingError as exc:
                repositories.fail_document(job.id, worker_id, str(exc))
                return
        if not stop_event.is_set():
            final = repositories.finalize_job(job.id, worker_id)
            logger.info("Job %s finished in state %s", job.id, final.state)
    except Exception as exc:
        logger.exception("Fatal processing error for job %s", job.id)
        repositories.fail_document(job.id, worker_id, str(exc))
    finally:
        heartbeat_stop.set()
        heartbeat.join(timeout=2)
        logger.info("Job %s worker RSS=%s KB", job.id, _max_rss_kb())


def _process_pages(settings: Settings, repositories: PostgresRepositories, blob_store: BlobStore, job: ProcessingJob, custodian_id: UUID, source_id: UUID, canonical_object_id: UUID, canonical_sha256: str, settings_digest: str, pdf: object, worker_id: str, stop_event: threading.Event) -> None:
    checkpoints = repositories.list_page_checkpoints(job.id, custodian_id)
    for checkpoint in checkpoints:
        if stop_event.is_set():
            return
        if checkpoint.state == "completed":
            continue
        attempts = checkpoint.attempt_count
        while attempts <= settings.worker_page_retry_limit:
            if stop_event.is_set():
                return
            current = repositories.mark_page_processing(job.id, checkpoint.page_number, worker_id)
            if current.state == "completed":
                break
            try:
                if settings.worker_fail_page_number == checkpoint.page_number:
                    raise PageProcessingError("Injected page failure.")
                processed = process_page(pdf, checkpoint.page_number)
                if settings.worker_page_delay_seconds:
                    time.sleep(settings.worker_page_delay_seconds)
                _persist_page(blob_store, repositories, job.id, checkpoint.page_number, custodian_id, source_id, canonical_object_id, canonical_sha256, settings_digest, processed.json_bytes, processed.render_bytes)
                logger.info("Job %s page %s committed; current RSS=%s KB", job.id, checkpoint.page_number, _current_rss_kb())
                break
            except PageProcessingError as exc:
                attempts += 1
                if attempts > settings.worker_page_retry_limit:
                    repositories.mark_page_failed(job.id, checkpoint.page_number, str(exc))
                    break
                repositories.mark_page_pending(job.id, checkpoint.page_number, str(exc))
                time.sleep(min(2**attempts, 10))


def _persist_page(blob_store: BlobStore, repositories: PostgresRepositories, job_id: UUID, page_number: int, custodian_id: UUID, source_id: UUID, canonical_object_id: UUID, canonical_sha256: str, settings_digest: str, json_bytes: bytes, render_bytes: bytes) -> None:
    json_id = uuid4()
    render_id = uuid4()
    json_stage = blob_store.stage_path(f"{job_id}-{page_number}-json.part")
    render_stage = blob_store.stage_path(f"{job_id}-{page_number}-render.part")
    try:
        _write_staged(json_stage, json_bytes)
        _write_staged(render_stage, render_bytes)
        json_sha = hashlib.sha256(json_bytes).hexdigest()
        render_sha = hashlib.sha256(render_bytes).hexdigest()
        json_blob = blob_store.put_derived(custodian_id, json_id, json_stage, json_sha, len(json_bytes), "application/json")
        render_blob = blob_store.put_derived(custodian_id, render_id, render_stage, render_sha, len(render_bytes), "image/png")
        common: dict[str, Any] = {"source_id": source_id, "custodian_id": custodian_id, "canonical_object_id": canonical_object_id, "canonical_sha256": canonical_sha256, "job_id": job_id, "schema_version": "0.1.0", "extractor_name": "pdfplumber-page-processor", "extractor_version": "0.1.0", "settings": {"resolution_dpi": 150, "coordinate_contract": "pdf-points-top-left"}, "settings_digest": settings_digest, "page_number": page_number, "created_at": datetime.now(timezone.utc)}
        json_representation = DerivedRepresentation(id=json_id, representation_kind="page-json", storage_key=json_blob.storage_key, content_sha256=json_sha, byte_size=len(json_bytes), **common)
        render_representation = DerivedRepresentation(id=render_id, representation_kind="page-render", storage_key=render_blob.storage_key, content_sha256=render_sha, byte_size=len(render_bytes), **common)
        repositories.commit_page_artifacts(job_id, page_number, json_representation, render_representation)
    finally:
        json_stage.unlink(missing_ok=True)
        render_stage.unlink(missing_ok=True)


def _write_staged(path: Path, content: bytes) -> None:
    with path.open("wb") as output:
        output.write(content)
        output.flush()
        os.fsync(output.fileno())


def _hash_stream(stream: object) -> str:
    digest = hashlib.sha256()
    while chunk := stream.read(1024 * 1024):  # type: ignore[attr-defined]
        digest.update(chunk)
    return digest.hexdigest()


def _settings_digest(settings: Settings) -> str:
    value = f"pdfplumber-page-processor|0.1.0|150|{settings.worker_page_retry_limit}"
    return hashlib.sha256(value.encode()).hexdigest()


def _max_rss_kb() -> int:
    try:
        import resource

        return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    except (ImportError, AttributeError):
        return 0


def _current_rss_kb() -> int:
    try:
        statm = Path("/proc/self/statm").read_text(encoding="ascii").split()
        page_size = os.sysconf("SC_PAGE_SIZE")
        return int(int(statm[1]) * page_size / 1024)
    except (FileNotFoundError, OSError, ValueError):
        return 0


def _install_signal_handlers(stop_event: threading.Event) -> None:
    def stop(_signum: int, _frame: object) -> None:
        stop_event.set()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run_forever(Settings.from_env())
