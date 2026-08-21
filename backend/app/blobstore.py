"""Canonical/derived blob boundary and local durable implementation."""

from __future__ import annotations

import hashlib
import os
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from tempfile import SpooledTemporaryFile
from typing import Any, BinaryIO, Iterator, Protocol, cast
from uuid import UUID


@dataclass(frozen=True)
class StoredBlob:
    storage_key: str
    sha256: str
    byte_size: int


class BlobStore(Protocol):
    def put_canonical(
        self,
        custodian_id: UUID,
        staged_path: Path,
        sha256: str,
        byte_size: int,
        content_type: str = "application/pdf",
    ) -> StoredBlob: ...

    def put_derived(
        self,
        custodian_id: UUID,
        representation_id: UUID,
        staged_path: Path,
        sha256: str,
        byte_size: int,
        content_type: str = "application/octet-stream",
    ) -> StoredBlob: ...

    def open(self, storage_key: str) -> BinaryIO: ...

    def stage_path(self, name: str) -> Path: ...

    def cleanup_staging(self, older_than_seconds: float = 24 * 60 * 60) -> int: ...

    def iter_chunks(self, storage_key: str, chunk_size: int = 1024 * 1024) -> Iterator[bytes]: ...

    def check(self) -> None: ...


class LocalFilesystemBlobStore:
    """Filesystem implementation with physically separate canonical/derived roots."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.canonical_root = root / "canonical"
        self.derived_root = root / "derived"
        self.staging_root = root / "staging"
        for directory in (self.canonical_root, self.derived_root, self.staging_root):
            directory.mkdir(parents=True, exist_ok=True)

    def put_canonical(
        self,
        custodian_id: UUID,
        staged_path: Path,
        sha256: str,
        byte_size: int,
        content_type: str = "application/pdf",
    ) -> StoredBlob:
        _validate_digest(sha256)
        key = f"canonical/{custodian_id}/{sha256[:2]}/{sha256}"
        return self._put(self.canonical_root / str(custodian_id) / sha256[:2] / sha256, key, staged_path, sha256, byte_size)

    def put_derived(
        self,
        custodian_id: UUID,
        representation_id: UUID,
        staged_path: Path,
        sha256: str,
        byte_size: int,
        content_type: str = "application/octet-stream",
    ) -> StoredBlob:
        _validate_digest(sha256)
        key = f"derived/{custodian_id}/{representation_id}/{sha256}"
        return self._put(self.derived_root / str(custodian_id) / str(representation_id) / sha256, key, staged_path, sha256, byte_size)

    def stage_path(self, name: str) -> Path:
        safe_name = Path(name).name
        if not safe_name:
            raise ValueError("A staging name is required.")
        return self.staging_root / safe_name

    def cleanup_staging(self, older_than_seconds: float = 24 * 60 * 60) -> int:
        """Remove stale upload parts without touching active or canonical objects."""
        cutoff = time.time() - older_than_seconds
        removed = 0
        for candidate in self.staging_root.glob("*.part"):
            try:
                if candidate.stat().st_mtime < cutoff:
                    candidate.unlink()
                    removed += 1
            except FileNotFoundError:
                continue
        return removed

    def open(self, storage_key: str) -> BinaryIO:
        path = self._resolve_key(storage_key)
        return path.open("rb")

    def _put(self, destination: Path, key: str, staged_path: Path, sha256: str, byte_size: int) -> StoredBlob:
        if not staged_path.is_file():
            raise FileNotFoundError(staged_path)
        if destination.exists():
            staged_path.unlink(missing_ok=True)
            return StoredBlob(key, sha256, byte_size)
        destination.parent.mkdir(parents=True, exist_ok=True)
        os.replace(staged_path, destination)
        staged_path.unlink(missing_ok=True)
        return StoredBlob(key, sha256, byte_size)

    def _resolve_key(self, storage_key: str) -> Path:
        candidate = (self.root / storage_key).resolve()
        root = self.root.resolve()
        if candidate != root and root not in candidate.parents:
            raise ValueError("Storage key escapes the blob-store root.")
        return candidate

    def iter_chunks(self, storage_key: str, chunk_size: int = 1024 * 1024) -> Iterator[bytes]:
        with self.open(storage_key) as handle:
            while chunk := handle.read(chunk_size):
                yield chunk

    def check(self) -> None:
        for directory in (self.canonical_root, self.derived_root, self.staging_root):
            directory.mkdir(parents=True, exist_ok=True)


class S3BlobStore:
    """S3-compatible store with staging/finalization and custodian-scoped keys."""

    def __init__(
        self,
        endpoint_url: str,
        region: str,
        bucket: str,
        access_key: str,
        secret_key: str,
        client: Any | None = None,
    ) -> None:
        self.bucket = bucket
        self.staging_root = Path(os.getenv("CORPUS_S3_STAGING_ROOT", "/tmp/corpus-s3-staging"))
        self.staging_root.mkdir(parents=True, exist_ok=True)
        self._client = client or self._make_client(endpoint_url, region, access_key, secret_key)

    @staticmethod
    def _make_client(endpoint_url: str, region: str, access_key: str, secret_key: str) -> Any:
        import boto3

        return boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            region_name=region,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )

    def put_canonical(
        self,
        custodian_id: UUID,
        staged_path: Path,
        sha256: str,
        byte_size: int,
        content_type: str = "application/pdf",
    ) -> StoredBlob:
        key = f"canonical/{custodian_id}/{sha256[:2]}/{sha256}"
        return self._finalize(custodian_id, key, staged_path, sha256, byte_size, content_type)

    def put_derived(
        self,
        custodian_id: UUID,
        representation_id: UUID,
        staged_path: Path,
        sha256: str,
        byte_size: int,
        content_type: str = "application/octet-stream",
    ) -> StoredBlob:
        key = f"derived/{custodian_id}/{representation_id}/{sha256}"
        return self._finalize(custodian_id, key, staged_path, sha256, byte_size, content_type)

    def open(self, storage_key: str) -> BinaryIO:
        response = self._client.get_object(Bucket=self.bucket, Key=_safe_remote_key(storage_key))
        spool = SpooledTemporaryFile(max_size=8 * 1024 * 1024, mode="w+b")
        try:
            shutil.copyfileobj(response["Body"], spool, length=1024 * 1024)
            spool.seek(0)
            return cast(BinaryIO, spool)
        except Exception:
            spool.close()
            raise

    def stage_path(self, name: str) -> Path:
        safe_name = Path(name).name
        if not safe_name:
            raise ValueError("A staging name is required.")
        return self.staging_root / safe_name

    def cleanup_staging(self, older_than_seconds: float = 24 * 60 * 60) -> int:
        """Remove stale local upload parts and remote staging objects."""
        cutoff = time.time() - older_than_seconds
        removed = 0
        for candidate in self.staging_root.glob("*.part"):
            try:
                if candidate.stat().st_mtime < cutoff:
                    candidate.unlink()
                    removed += 1
            except FileNotFoundError:
                continue
        # Remote staging objects are best-effort cleanup: an interrupted process
        # must never make admission fail merely because a cleanup listing is
        # unavailable.  S3-compatible providers expose LastModified as UTC.
        try:
            paginator = self._client.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=self.bucket, Prefix="staging/"):
                for item in page.get("Contents", []):
                    modified = item.get("LastModified")
                    key = item.get("Key")
                    if not key or modified is None:
                        continue
                    if modified.timestamp() < cutoff:
                        self._client.delete_object(Bucket=self.bucket, Key=key)
                        removed += 1
        except (AttributeError, NotImplementedError):
            # Small fakes and minimal S3-compatible implementations may not
            # provide listing; local staging cleanup still remains safe.
            pass
        return removed

    def iter_chunks(self, storage_key: str, chunk_size: int = 1024 * 1024) -> Iterator[bytes]:
        response = self._client.get_object(Bucket=self.bucket, Key=_safe_remote_key(storage_key))
        body = response["Body"]
        try:
            while chunk := body.read(chunk_size):
                yield chunk
        finally:
            body.close()

    def check(self) -> None:
        self._client.head_bucket(Bucket=self.bucket)

    def _finalize(
        self,
        custodian_id: UUID,
        final_key: str,
        staged_path: Path,
        sha256: str,
        byte_size: int,
        content_type: str,
    ) -> StoredBlob:
        _validate_digest(sha256)
        if not staged_path.is_file():
            raise FileNotFoundError(staged_path)
        existing = self._head(final_key)
        if existing is not None:
            if int(existing.get("ContentLength", -1)) != byte_size:
                raise OSError("Existing object size does not match canonical metadata.")
            existing_digest = _metadata_digest(existing)
            if existing_digest is not None and existing_digest != sha256:
                raise OSError("Existing object digest does not match canonical metadata.")
            staged_path.unlink(missing_ok=True)
            return StoredBlob(final_key, sha256, byte_size)
        staging_key = f"staging/{custodian_id}/{UUID(int=int.from_bytes(os.urandom(16), 'big'))}.part"
        try:
            self._client.upload_file(
                str(staged_path),
                self.bucket,
                staging_key,
                ExtraArgs={"ContentType": content_type, "Metadata": {"sha256": sha256}},
            )
            staged_head = self._head(staging_key)
            if staged_head is None or int(staged_head.get("ContentLength", -1)) != byte_size:
                raise OSError("Staged object size could not be verified.")
            staged_digest = _metadata_digest(staged_head)
            if staged_digest is not None and staged_digest != sha256:
                raise OSError("Staged object digest could not be verified.")
            self._client.copy_object(
                Bucket=self.bucket,
                Key=final_key,
                CopySource={"Bucket": self.bucket, "Key": staging_key},
                MetadataDirective="REPLACE",
                ContentType=content_type,
                Metadata={"sha256": sha256},
            )
            final_head = self._head(final_key)
            if final_head is None or int(final_head.get("ContentLength", -1)) != byte_size:
                raise OSError("Final object was not available after finalization.")
            final_digest = _metadata_digest(final_head)
            if final_digest is not None and final_digest != sha256:
                raise OSError("Final object digest could not be verified.")
            return StoredBlob(final_key, sha256, byte_size)
        finally:
            try:
                self._client.delete_object(Bucket=self.bucket, Key=staging_key)
            except Exception:
                pass
            staged_path.unlink(missing_ok=True)

    def _head(self, key: str) -> dict[str, Any] | None:
        try:
            return cast(dict[str, Any], self._client.head_object(Bucket=self.bucket, Key=key))
        except Exception as exc:
            if _is_not_found(exc):
                return None
            raise


def hash_file(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def _validate_digest(value: str) -> None:
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise ValueError("sha256 must be a lowercase 64-character hexadecimal digest.")


def _safe_remote_key(value: str) -> str:
    if not value or value.startswith("/") or ".." in Path(value).parts:
        raise ValueError("Storage key is not a safe object key.")
    return value


def _is_not_found(error: Exception) -> bool:
    response = getattr(error, "response", None)
    return isinstance(response, dict) and response.get("Error", {}).get("Code") in {"404", "NoSuchKey", "NotFound"}


def _metadata_digest(response: dict[str, Any]) -> str | None:
    metadata = response.get("Metadata")
    if not isinstance(metadata, dict):
        return None
    value = metadata.get("sha256") or metadata.get("Sha256")
    return str(value) if value else None


def create_blob_store(settings: Any) -> BlobStore:
    if settings.blob_store_backend == "local":
        return LocalFilesystemBlobStore(settings.blob_store_root)
    return S3BlobStore(
        endpoint_url=settings.s3_endpoint_url,
        region=settings.s3_region,
        bucket=settings.s3_bucket,
        access_key=settings.s3_access_key,
        secret_key=settings.s3_secret_key,
    )
