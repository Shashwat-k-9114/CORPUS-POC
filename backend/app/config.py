"""Validated runtime configuration for the durable Corpus foundation."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


class ConfigurationError(ValueError):
    """Raised when required runtime configuration is missing or invalid."""


@dataclass(frozen=True)
class Settings:
    database_url: str
    blob_store_root: Path
    blob_store_backend: str = "local"
    s3_endpoint_url: str | None = None
    s3_region: str | None = None
    s3_bucket: str | None = None
    s3_access_key: str | None = None
    s3_secret_key: str | None = None
    review_token: str | None = None
    rate_limit_per_minute: int = 120
    max_upload_size_bytes: int = 20 * 1024 * 1024
    worker_poll_seconds: float = 2.0
    worker_lease_seconds: int = 30
    worker_page_retry_limit: int = 2
    worker_page_delay_seconds: float = 0.0
    worker_fail_page_number: int | None = None
    environment: str = "development"

    @classmethod
    def from_env(cls, environ: dict[str, str] | None = None) -> Settings:
        env = os.environ if environ is None else environ
        database_url = env.get(
            "CORPUS_DATABASE_URL",
            "postgresql://corpus:corpus@localhost:5432/corpus",
        ).strip()
        blob_root = env.get(
            "CORPUS_BLOB_STORE_ROOT",
            str(Path(__file__).resolve().parents[1] / "data" / "blobs"),
        ).strip()
        if not database_url:
            raise ConfigurationError("CORPUS_DATABASE_URL must not be empty.")
        parsed = urlparse(database_url)
        if parsed.scheme not in {"postgres", "postgresql"} or not parsed.hostname:
            raise ConfigurationError(
                "CORPUS_DATABASE_URL must be a PostgreSQL URL with a hostname."
            )
        if not blob_root:
            raise ConfigurationError("CORPUS_BLOB_STORE_ROOT must not be empty.")

        backend = env.get("CORPUS_BLOB_STORE_BACKEND", "local").strip().lower()
        if backend not in {"local", "s3"}:
            raise ConfigurationError("CORPUS_BLOB_STORE_BACKEND must be local or s3.")
        s3_endpoint = env.get("CORPUS_S3_ENDPOINT_URL", "").strip() or None
        s3_region = env.get("CORPUS_S3_REGION", "").strip() or None
        s3_bucket = env.get("CORPUS_S3_BUCKET", "").strip() or None
        s3_access_key = env.get("CORPUS_S3_ACCESS_KEY", "").strip() or None
        s3_secret_key = env.get("CORPUS_S3_SECRET_KEY", "").strip() or None
        if backend == "s3" and not all((s3_endpoint, s3_region, s3_bucket, s3_access_key, s3_secret_key)):
            raise ConfigurationError(
                "S3 blob storage requires CORPUS_S3_ENDPOINT_URL, CORPUS_S3_REGION, "
                "CORPUS_S3_BUCKET, CORPUS_S3_ACCESS_KEY and CORPUS_S3_SECRET_KEY."
            )

        max_upload = _positive_int(env.get("CORPUS_MAX_UPLOAD_SIZE_BYTES", str(20 * 1024 * 1024)), "CORPUS_MAX_UPLOAD_SIZE_BYTES")
        if max_upload > 50 * 1024 * 1024:
            raise ConfigurationError("CORPUS_MAX_UPLOAD_SIZE_BYTES must not exceed 50 MiB.")
        poll_seconds = _positive_float(env.get("CORPUS_WORKER_POLL_SECONDS", "2"), "CORPUS_WORKER_POLL_SECONDS")
        lease_seconds = _positive_int(env.get("CORPUS_WORKER_LEASE_SECONDS", "30"), "CORPUS_WORKER_LEASE_SECONDS")
        retry_limit = _nonnegative_int(env.get("CORPUS_WORKER_PAGE_RETRY_LIMIT", "2"), "CORPUS_WORKER_PAGE_RETRY_LIMIT")
        page_delay = _nonnegative_float(env.get("CORPUS_WORKER_PAGE_DELAY_SECONDS", "0"), "CORPUS_WORKER_PAGE_DELAY_SECONDS")
        failure_page_value = env.get("CORPUS_WORKER_FAIL_PAGE_NUMBER", "").strip()
        failure_page = _positive_int(failure_page_value, "CORPUS_WORKER_FAIL_PAGE_NUMBER") if failure_page_value else None
        environment = env.get("CORPUS_ENVIRONMENT", "development").strip() or "development"
        review_token = env.get("CORPUS_REVIEW_TOKEN", "").strip() or None
        if environment == "production" and not review_token:
            raise ConfigurationError("CORPUS_REVIEW_TOKEN is required in production.")
        rate_limit = _positive_int(env.get("CORPUS_RATE_LIMIT_PER_MINUTE", "120"), "CORPUS_RATE_LIMIT_PER_MINUTE")
        return cls(
            database_url=database_url,
            blob_store_root=Path(blob_root),
            blob_store_backend=backend,
            s3_endpoint_url=s3_endpoint,
            s3_region=s3_region,
            s3_bucket=s3_bucket,
            s3_access_key=s3_access_key,
            s3_secret_key=s3_secret_key,
            review_token=review_token,
            rate_limit_per_minute=rate_limit,
            max_upload_size_bytes=max_upload,
            worker_poll_seconds=poll_seconds,
            worker_lease_seconds=lease_seconds,
            worker_page_retry_limit=retry_limit,
            worker_page_delay_seconds=page_delay,
            worker_fail_page_number=failure_page,
            environment=environment,
        )


def _positive_int(value: str, name: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ConfigurationError(f"{name} must be a positive integer.") from exc
    if parsed <= 0:
        raise ConfigurationError(f"{name} must be a positive integer.")
    return parsed


def _positive_float(value: str, name: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ConfigurationError(f"{name} must be a positive number.") from exc
    if parsed <= 0:
        raise ConfigurationError(f"{name} must be a positive number.")
    return parsed


def _nonnegative_int(value: str, name: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ConfigurationError(f"{name} must be a non-negative integer.") from exc
    if parsed < 0:
        raise ConfigurationError(f"{name} must be a non-negative integer.")
    return parsed


def _nonnegative_float(value: str, name: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ConfigurationError(f"{name} must be a non-negative number.") from exc
    if parsed < 0:
        raise ConfigurationError(f"{name} must be a non-negative number.")
    return parsed
