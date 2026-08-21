from pathlib import Path
from uuid import UUID, uuid4

import pytest

from app.blobstore import LocalFilesystemBlobStore, hash_file
from app.config import ConfigurationError, Settings


def test_settings_validate_postgres_url_and_positive_limits(tmp_path: Path):
    settings = Settings.from_env(
        {
            "CORPUS_DATABASE_URL": "postgresql://user:pass@db:5432/corpus",
            "CORPUS_BLOB_STORE_ROOT": str(tmp_path),
            "CORPUS_MAX_UPLOAD_SIZE_BYTES": "123",
            "CORPUS_WORKER_POLL_SECONDS": "0.5",
        }
    )
    assert settings.database_url.startswith("postgresql://")
    assert settings.max_upload_size_bytes == 123
    assert settings.worker_poll_seconds == 0.5


@pytest.mark.parametrize(
    "overrides",
    [
        {"CORPUS_DATABASE_URL": "sqlite:///not-postgres"},
        {"CORPUS_DATABASE_URL": "postgresql://"},
        {"CORPUS_MAX_UPLOAD_SIZE_BYTES": "0"},
        {"CORPUS_WORKER_POLL_SECONDS": "nope"},
    ],
)
def test_settings_reject_invalid_values(overrides):
    environment = {
        "CORPUS_DATABASE_URL": "postgresql://user:pass@db:5432/corpus",
        "CORPUS_BLOB_STORE_ROOT": "C:/tmp/corpus-blobs",
    }
    environment.update(overrides)
    with pytest.raises(ConfigurationError):
        Settings.from_env(environment)


def test_local_blobstore_separates_custodian_canonical_objects(tmp_path: Path):
    store = LocalFilesystemBlobStore(tmp_path)
    first = uuid4()
    second = uuid4()
    source = tmp_path / "input.part"
    source.write_bytes(b"same bytes")
    digest, size = hash_file(source)

    first_blob = store.put_canonical(first, source, digest, size)
    source.write_bytes(b"same bytes")
    second_blob = store.put_canonical(second, source, digest, size)

    assert first_blob.storage_key != second_blob.storage_key
    assert first_blob.storage_key.startswith(f"canonical/{first}/")
    assert second_blob.storage_key.startswith(f"canonical/{second}/")
    with store.open(first_blob.storage_key) as handle:
        assert handle.read() == b"same bytes"
    with store.open(second_blob.storage_key) as handle:
        assert handle.read() == b"same bytes"


def test_local_blobstore_rejects_path_escape(tmp_path: Path):
    store = LocalFilesystemBlobStore(tmp_path)
    with pytest.raises(ValueError):
        store.open("../outside")


def test_blobstore_rejects_uppercase_or_invalid_digest(tmp_path: Path):
    store = LocalFilesystemBlobStore(tmp_path)
    with pytest.raises(ValueError):
        store.put_canonical(UUID(int=1), tmp_path / "missing", "A" * 64, 0)
