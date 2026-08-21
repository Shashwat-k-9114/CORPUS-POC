from __future__ import annotations

import io
from pathlib import Path
from uuid import uuid4

import pytest

from app.blobstore import S3BlobStore


class MissingObject(Exception):
    response = {"Error": {"Code": "404"}}


class FakeS3:
    def __init__(self, fail_after_copy: bool = False) -> None:
        self.objects: dict[str, bytes] = {}
        self.metadata: dict[str, dict[str, object]] = {}
        self.fail_after_copy = fail_after_copy

    def upload_file(self, filename: str, bucket: str, key: str, ExtraArgs: dict[str, object]) -> None:
        self.objects[key] = Path(filename).read_bytes()
        self.metadata[key] = {"ContentLength": len(self.objects[key]), **ExtraArgs}

    def head_object(self, Bucket: str, Key: str) -> dict[str, object]:
        if Key not in self.objects:
            raise MissingObject()
        if self.fail_after_copy and not Key.startswith("staging/"):
            raise OSError("metadata service unavailable")
        return self.metadata[Key]

    def copy_object(self, Bucket: str, Key: str, CopySource: dict[str, str], **kwargs: object) -> None:
        self.objects[Key] = self.objects[CopySource["Key"]]
        self.metadata[Key] = {"ContentLength": len(self.objects[Key]), **kwargs}

    def delete_object(self, Bucket: str, Key: str) -> None:
        self.objects.pop(Key, None)
        self.metadata.pop(Key, None)

    def get_object(self, Bucket: str, Key: str) -> dict[str, io.BytesIO]:
        return {"Body": io.BytesIO(self.objects[Key])}

    def head_bucket(self, Bucket: str) -> None:
        return None


def make_store(client: FakeS3) -> S3BlobStore:
    return S3BlobStore("https://storage.example", "us-east-1", "private", "access", "secret", client=client)


def test_s3_canonical_upload_download_and_custodian_scoping(tmp_path: Path) -> None:
    payload = b"%PDF-1.7\nprivate canonical bytes"
    staged = tmp_path / "upload.part"
    staged.write_bytes(payload)
    digest = __import__("hashlib").sha256(payload).hexdigest()
    client = FakeS3()
    store = make_store(client)

    result = store.put_canonical(uuid4(), staged, digest, len(payload), "application/pdf")

    assert result.storage_key.startswith("canonical/")
    assert result.storage_key in client.objects
    assert b"".join(store.iter_chunks(result.storage_key, 4)) == payload
    store.check()
    assert not any(key.startswith("staging/") for key in client.objects)


def test_s3_derived_artifact_uses_separate_namespace(tmp_path: Path) -> None:
    payload = b"{}"
    staged = tmp_path / "derived.part"
    staged.write_bytes(payload)
    digest = __import__("hashlib").sha256(payload).hexdigest()
    result = make_store(FakeS3()).put_derived(uuid4(), uuid4(), staged, digest, len(payload), "application/json")
    assert result.storage_key.startswith("derived/")


def test_s3_failure_after_copy_leaves_final_for_safe_retry_and_cleans_staging(tmp_path: Path) -> None:
    payload = b"%PDF-1.7\nbytes"
    staged = tmp_path / "upload.part"
    staged.write_bytes(payload)
    digest = __import__("hashlib").sha256(payload).hexdigest()
    client = FakeS3(fail_after_copy=True)
    store = make_store(client)

    with pytest.raises(OSError):
        store.put_canonical(uuid4(), staged, digest, len(payload))

    assert not any(key.startswith("staging/") for key in client.objects)
    assert any(key.startswith("canonical/") for key in client.objects)
