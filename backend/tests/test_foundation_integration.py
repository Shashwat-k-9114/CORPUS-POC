import os
from pathlib import Path
from uuid import uuid4

import pytest

from app.blobstore import LocalFilesystemBlobStore, hash_file
from app.database import Database
from app.db.migrate import apply_migrations
from app.repositories import PostgresRepositories

DATABASE_URL = os.environ.get("CORPUS_TEST_DATABASE_URL")
pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def repositories(tmp_path_factory: pytest.TempPathFactory):
    if not DATABASE_URL:
        pytest.skip("CORPUS_TEST_DATABASE_URL is not configured")
    apply_migrations(DATABASE_URL)
    database = Database(DATABASE_URL)
    assert database.ping()
    return PostgresRepositories(database)


def test_migration_seeds_default_custodian_and_corpus(repositories: PostgresRepositories):
    custodians = repositories.list_custodians()
    assert any(custodian.slug == "default" for custodian in custodians)
    default = next(custodian for custodian in custodians if custodian.slug == "default")
    corpus = repositories.get_default_for_custodian(default.id)
    assert corpus is not None
    assert corpus.custodian_id == default.id
    assert corpus.kind == "custodian"


def test_source_registration_is_exactly_deduplicated_within_custodian(
    repositories: PostgresRepositories, tmp_path: Path
):
    default = next(custodian for custodian in repositories.list_custodians() if custodian.slug == "default")
    corpus = repositories.get_default_for_custodian(default.id)
    assert corpus is not None
    store = LocalFilesystemBlobStore(tmp_path)
    staged = store.stage_path("source.part")
    staged.write_bytes(f"durable source bytes {uuid4()}".encode())
    digest, size = hash_file(staged)
    stored = store.put_canonical(default.id, staged, digest, size)

    first = repositories.register(
        custodian_id=default.id,
        corpus_id=corpus.id,
        sha256=digest,
        byte_size=size,
        media_type="application/octet-stream",
        storage_key=stored.storage_key,
        display_name="first.bin",
        claimed_origin="test-origin",
        obtained_from="test-upload",
        arrival_channel="test",
        original_filename="first.bin",
    )
    second = repositories.register(
        custodian_id=default.id,
        corpus_id=corpus.id,
        sha256=digest,
        byte_size=size,
        media_type="application/octet-stream",
        storage_key=stored.storage_key,
        display_name="second.bin",
        claimed_origin="test-origin-2",
        obtained_from="test-upload-2",
        arrival_channel="test",
        original_filename="second.bin",
    )
    assert first[0].id == second[0].id
    assert first[1].id == second[1].id
    assert first[4] is False
    assert second[4] is True
    assert first[2].id != second[2].id
    assert first[3].id == second[3].id


def test_processing_job_survives_a_new_repository_instance(repositories: PostgresRepositories):
    default = next(custodian for custodian in repositories.list_custodians() if custodian.slug == "default")
    corpus = repositories.get_default_for_custodian(default.id)
    assert corpus is not None
    digest = uuid4().hex * 2
    source = repositories.register(
        custodian_id=default.id,
        corpus_id=corpus.id,
        sha256=digest,
        byte_size=1,
        media_type="application/octet-stream",
        storage_key=f"canonical/{default.id}/{digest[:2]}/{digest}",
        display_name="job-source.bin",
        claimed_origin="test",
        obtained_from="test",
        arrival_channel="test",
        original_filename="job-source.bin",
    )[0]
    created = repositories.create_processing_job(source.id, "foundation-placeholder", "0.1.0")
    fresh = PostgresRepositories(repositories.database)
    jobs = fresh.list_processing_jobs()
    restored = next(job for job in jobs if job.id == created.id)
    assert restored.state == "queued"
    assert restored.source_id == source.id
    checkpoints = fresh.ensure_page_checkpoints(created.id, 2)
    assert [checkpoint.page_number for checkpoint in checkpoints] == [1, 2]
    assert fresh.get_page_checkpoint(created.id, 2) == checkpoints[1]
