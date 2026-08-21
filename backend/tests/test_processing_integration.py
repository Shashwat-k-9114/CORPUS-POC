import os
from pathlib import Path
from uuid import uuid4

import pytest

from app.blobstore import LocalFilesystemBlobStore, hash_file
from app.database import Database
from app.db.migrate import apply_migrations
from app.repositories import PostgresRepositories
from tests.pdf_fixtures import build_multi_page_pdf

DATABASE_URL = os.environ.get("CORPUS_TEST_DATABASE_URL")
pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def repositories() -> PostgresRepositories:
    if not DATABASE_URL:
        pytest.skip("CORPUS_TEST_DATABASE_URL is not configured")
    apply_migrations(DATABASE_URL)
    database = Database(DATABASE_URL)
    assert database.ping()
    return PostgresRepositories(database)


def _queued_job(repositories: PostgresRepositories, tmp_path: Path):
    custodian, corpus = repositories.create_custodian_with_default_corpus(f"worker-{uuid4().hex[:12]}", "Worker test")
    store = LocalFilesystemBlobStore(tmp_path)
    staged = store.stage_path("source.part")
    staged.write_bytes(build_multi_page_pdf(2))
    digest, size = hash_file(staged)
    stored = store.put_canonical(custodian.id, staged, digest, size)
    source = repositories.register(
        custodian_id=custodian.id,
        corpus_id=corpus.id,
        sha256=digest,
        byte_size=size,
        media_type="application/pdf",
        storage_key=stored.storage_key,
        display_name="worker.pdf",
        claimed_origin="test",
        obtained_from="test",
        arrival_channel="integration",
        original_filename="worker.pdf",
    )[0]
    return custodian, source, repositories.create_processing_job(source.id, "pdf-page", "0.1.0", priority=100)


def test_claim_is_exclusive_and_heartbeat_extends_lease(repositories: PostgresRepositories, tmp_path: Path) -> None:
    custodian, _, job = _queued_job(repositories, tmp_path)
    first = repositories.claim_job("integration-worker-a", 60)
    assert first is not None and first.id == job.id
    second = repositories.claim_job("integration-worker-b", 60)
    assert second is None or second.id != job.id
    before = repositories.get_processing_job(job.id, custodian.id)
    assert before is not None and before.lease_expires_at is not None
    repositories.heartbeat_job(job.id, "integration-worker-a", 120)
    after = repositories.get_processing_job(job.id, custodian.id)
    assert after is not None and after.heartbeat_at is not None
    assert after.lease_expires_at is not None and after.lease_expires_at > before.lease_expires_at
    attempts = repositories.list_attempts(job.id, custodian.id)
    assert len(attempts) == 1 and attempts[0].worker_id == "integration-worker-a"


def test_expired_lease_returns_to_queue_and_checkpoints_are_idempotent(
    repositories: PostgresRepositories, tmp_path: Path
) -> None:
    custodian, _, job = _queued_job(repositories, tmp_path)
    claimed = repositories.claim_job("integration-worker-expiring", 60)
    assert claimed is not None
    checkpoints = repositories.ensure_page_checkpoints(job.id, 2)
    again = repositories.ensure_page_checkpoints(job.id, 2)
    assert [item.id for item in again] == [item.id for item in checkpoints]
    with repositories.database.connection() as connection:
        connection.execute(
            "UPDATE processing_jobs SET lease_expires_at = now() - interval '1 second' WHERE id = %s",
            (job.id,),
        )
    # The live Compose worker may also recover another expired lease left by a
    # prior acceptance run; this test's durable job is the authoritative check.
    assert repositories.recover_expired_jobs() >= 1
    restored = repositories.get_processing_job(job.id, custodian.id)
    assert restored is not None and restored.state == "queued" and restored.lease_owner is None
    assert repositories.list_attempts(job.id, custodian.id)[0].outcome == "interrupted"
