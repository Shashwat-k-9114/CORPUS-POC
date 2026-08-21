import hashlib
import hmac
import json
import os
import time
import uuid
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable, Iterator
from dataclasses import asdict
from pathlib import Path
from typing import Any
from uuid import UUID

import psycopg
from fastapi import FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response, StreamingResponse
from pydantic import BaseModel

from app import storage
from app.blobstore import create_blob_store
from app.config import ConfigurationError, Settings
from app.database import Database
from app.extraction import InvalidPDFError, extract_document
from app.models import DocumentExtractionResponse
from app.rendering import DEFAULT_RESOLUTION_DPI, PageRenderError, render_page_png
from app.repositories import IdempotencyConflict, PostgresRepositories

app = FastAPI(title="Corpus API", version="0.1.0")

_rate_windows: dict[str, deque[float]] = defaultdict(deque)

MAX_UPLOAD_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB
PDF_MAGIC = b"%PDF-"
UPLOAD_CHUNK_SIZE = 1024 * 1024  # 1 MB
ADMISSION_PIPELINE_NAME = "pdf-page-processing"
ADMISSION_PIPELINE_VERSION = "0.1.0"

# CORS: the frontend (Next.js, a different origin) calls this API directly from the
# browser and must read the coordinate-mapping headers off the image response, which
# requires an explicit allow-list and expose_headers (see BUILD_LOG.md, Phase 5).
DEFAULT_ALLOWED_ORIGINS = "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001"
_allowed_origins = [
    origin.strip()
    for origin in os.environ.get("CORPUS_ALLOWED_ORIGINS", DEFAULT_ALLOWED_ORIGINS).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
    expose_headers=[
        "X-Page-Number",
        "X-Page-Width-Points",
        "X-Page-Height-Points",
        "X-Image-Width-Px",
        "X-Image-Height-Px",
        "X-Resolution-Dpi",
    ],
)


@app.middleware("http")
async def security_middleware(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    path = request.url.path
    if path not in {"/health", "/ready"} and (path.startswith("/v1/") or path.startswith("/extract") or path.startswith("/documents/")):
        try:
            settings = Settings.from_env()
        except ConfigurationError as exc:
            return JSONResponse({"detail": str(exc)}, status_code=503)
        if settings.review_token:
            supplied = request.headers.get("X-Corpus-Review-Token", "")
            if not supplied or not hmac.compare_digest(supplied, settings.review_token):
                return JSONResponse({"detail": "Review access token required."}, status_code=401, headers={"WWW-Authenticate": "X-Corpus-Review-Token"})
        client = request.client.host if request.client else "unknown"
        now = time.monotonic()
        window = _rate_windows[client]
        while window and now - window[0] >= 60:
            window.popleft()
        if len(window) >= settings.rate_limit_per_minute:
            return JSONResponse({"detail": "Request rate limit exceeded; retry shortly."}, status_code=429)
        window.append(now)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


class CustodianCreateRequest(BaseModel):
    slug: str
    name: str


class ProcessingJobCreateRequest(BaseModel):
    source_id: UUID
    pipeline_name: str
    pipeline_version: str
    priority: int = 0


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="corpus-backend", version=app.version)


@app.get("/ready")
def ready() -> dict[str, str]:
    """Readiness probe for the durable foundation; liveness remains dependency-free."""
    try:
        settings = Settings.from_env()
        if not Database(settings.database_url).ping():
            raise HTTPException(status_code=503, detail="Database is unavailable.")
        create_blob_store(settings).check()
    except ConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"status": "ready", "service": "corpus-backend"}


@app.get("/v1/custodians")
def list_custodians() -> list[dict[str, object]]:
    repositories = _repositories()
    return [_serialize(asdict(custodian)) for custodian in repositories.list_custodians()]


@app.post("/v1/custodians", status_code=201)
def create_custodian(request: CustodianCreateRequest) -> dict[str, object]:
    slug = request.slug.strip()
    name = request.name.strip()
    if not slug or not name:
        raise HTTPException(status_code=422, detail="Custodian slug and name are required.")
    try:
        custodian, corpus = _repositories().create_custodian_with_default_corpus(
            slug, name
        )
    except psycopg.errors.UniqueViolation as exc:
        raise HTTPException(status_code=409, detail="Custodian slug already exists.") from exc
    return {"custodian": _serialize(asdict(custodian)), "default_corpus": _serialize(asdict(corpus))}


@app.get("/v1/custodians/{custodian_id}/corpora")
def list_custodian_corpora(custodian_id: UUID) -> list[dict[str, object]]:
    """Return corpora owned by a custodian without crossing tenant boundaries."""
    repositories = _repositories()
    if repositories.get_custodian(custodian_id) is None:
        raise HTTPException(status_code=404, detail="Custodian not found.")
    corpus = repositories.get_default_for_custodian(custodian_id)
    return [_serialize(asdict(corpus))] if corpus is not None else []


@app.post("/v1/admissions", status_code=201)
@app.post("/v1/sources", status_code=201)
def admit_source(
    file: UploadFile = File(...),
    custodian_id: str = Form(...),
    corpus_id: str = Form(...),
    claimed_origin: str | None = Form(default=None),
    obtained_from: str | None = Form(default=None),
    arrival_channel: str = Form(...),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict[str, object]:
    """Stream, durably admit, and queue a PDF without running extraction."""
    try:
        custodian_uuid = UUID(custodian_id)
        corpus_uuid = UUID(corpus_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="custodian_id and corpus_id must be UUIDs.") from exc
    repositories = _repositories()
    if repositories.get_custodian(custodian_uuid) is None:
        raise HTTPException(status_code=404, detail="Custodian not found.")
    if repositories.get_for_custodian(corpus_uuid, custodian_uuid) is None:
        raise HTTPException(status_code=409, detail="The corpus does not belong to the supplied custodian.")
    if idempotency_key is not None:
        idempotency_key = idempotency_key.strip()
        if not idempotency_key or len(idempotency_key) > 255:
            raise HTTPException(status_code=422, detail="Idempotency-Key must be 1-255 characters.")
    settings = Settings.from_env()
    blob_store = create_blob_store(settings)
    blob_store.cleanup_staging()
    stage = blob_store.stage_path(f"{uuid.uuid4().hex}.part")
    try:
        sha256, byte_size = _stream_pdf_to_stage(file, stage, settings.max_upload_size_bytes)
        stored = blob_store.put_canonical(custodian_uuid, stage, sha256, byte_size, file.content_type or "application/pdf")
        try:
            fingerprint = _admission_fingerprint(
                sha256=sha256,
                byte_size=byte_size,
                media_type=file.content_type or "application/pdf",
                display_name=Path(file.filename or "source").name,
                corpus_id=corpus_uuid,
                arrival_channel=arrival_channel,
                claimed_origin=claimed_origin or "",
                obtained_from=obtained_from or "",
            )
            receipt = repositories.admit(
                custodian_id=custodian_uuid,
                corpus_id=corpus_uuid,
                sha256=sha256,
                byte_size=byte_size,
                media_type=file.content_type or "application/pdf",
                storage_key=stored.storage_key,
                display_name=Path(file.filename or "source").name,
                claimed_origin=claimed_origin or "",
                obtained_from=obtained_from or "",
                arrival_channel=arrival_channel,
                original_filename=file.filename,
                idempotency_key=idempotency_key,
                request_fingerprint=fingerprint,
                pipeline_name=ADMISSION_PIPELINE_NAME,
                pipeline_version=ADMISSION_PIPELINE_VERSION,
            )
        except IdempotencyConflict as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    finally:
        stage.unlink(missing_ok=True)
    return {
        "source": _serialize(asdict(receipt.source)),
        "canonical_object": _serialize(asdict(receipt.canonical_object)),
        "arrival": _serialize(asdict(receipt.arrival)),
        "enrollment": _serialize(asdict(receipt.enrollment)),
        "processing_job": _serialize(asdict(receipt.processing_job)),
        "exact_duplicate": receipt.exact_duplicate,
        "idempotent_replay": receipt.idempotent_replay,
    }


@app.post("/v1/processing-jobs", status_code=201)
def create_processing_job(request: ProcessingJobCreateRequest) -> dict[str, Any]:
    if request.priority < 0:
        raise HTTPException(status_code=422, detail="priority must be zero or greater.")
    if _repositories().get_source(request.source_id) is None:
        raise HTTPException(status_code=404, detail="Source not found.")
    job = _repositories().create_processing_job(
        request.source_id, request.pipeline_name, request.pipeline_version, request.priority
    )
    serialized = _serialize(asdict(job))
    if not isinstance(serialized, dict):
        raise RuntimeError("Processing job serialization returned a non-object.")
    return serialized


@app.get("/v1/processing-jobs")
def list_processing_jobs(
    custodian_id: UUID, state: str | None = None, limit: int = 50, offset: int = 0
) -> dict[str, object]:
    if state is not None and state not in {"queued", "processing", "completed", "partial", "failed"}:
        raise HTTPException(status_code=422, detail="Invalid processing job state.")
    if limit < 1 or limit > 100 or offset < 0:
        raise HTTPException(status_code=422, detail="Invalid pagination values.")
    jobs, total = _repositories().list_processing_jobs_page(custodian_id, state, limit, offset)
    return {"items": [_serialize(asdict(job)) for job in jobs], "total": total, "limit": limit, "offset": offset}


@app.get("/v1/processing-jobs/{job_id}")
def get_processing_job(job_id: UUID, custodian_id: UUID) -> dict[str, object]:
    job = _repositories().get_processing_job(job_id, custodian_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Processing job not found.")
    serialized = _serialize(asdict(job))
    if not isinstance(serialized, dict):
        raise RuntimeError("Processing job serialization returned a non-object.")
    return serialized


@app.get("/v1/processing-jobs/{job_id}/pages")
def list_processing_pages(job_id: UUID, custodian_id: UUID) -> list[dict[str, object]]:
    if _repositories().get_processing_job(job_id, custodian_id) is None:
        raise HTTPException(status_code=404, detail="Processing job not found.")
    return [_serialize(asdict(item)) for item in _repositories().list_page_checkpoints(job_id, custodian_id)]


@app.get("/v1/processing-jobs/{job_id}/attempts")
def list_processing_attempts(job_id: UUID, custodian_id: UUID) -> list[dict[str, object]]:
    if _repositories().get_processing_job(job_id, custodian_id) is None:
        raise HTTPException(status_code=404, detail="Processing job not found.")
    return [_serialize(asdict(item)) for item in _repositories().list_attempts(job_id, custodian_id)]


@app.post("/v1/processing-jobs/{job_id}/retry")
def retry_processing_job(job_id: UUID, custodian_id: UUID) -> dict[str, object]:
    try:
        job = _repositories().retry_job(job_id, custodian_id)
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(status_code=404 if "not found" in detail.lower() else 409, detail=detail) from exc
    serialized = _serialize(asdict(job))
    if not isinstance(serialized, dict):
        raise RuntimeError("Processing job serialization returned a non-object.")
    return serialized


@app.get("/v1/workers")
def list_workers() -> list[dict[str, object]]:
    return [_serialize(asdict(item)) for item in _repositories().list_worker_heartbeats()]


@app.get("/v1/sources")
def list_sources(
    custodian_id: UUID,
    corpus_id: UUID,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, object]:
    return _list_sources_response(custodian_id, corpus_id, limit, offset)


@app.get("/v1/custodians/{custodian_id}/sources")
def list_custodian_sources(
    custodian_id: UUID,
    corpus_id: UUID,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, object]:
    return _list_sources_response(custodian_id, corpus_id, limit, offset)


@app.get("/v1/sources/{source_id}")
def get_source(source_id: UUID, custodian_id: UUID) -> dict[str, object]:
    repositories = _repositories()
    source = repositories.get_source_for_custodian(source_id, custodian_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found.")
    return _source_response(repositories, source, custodian_id)


@app.get("/v1/custodians/{custodian_id}/sources/{source_id}")
def get_custodian_source(custodian_id: UUID, source_id: UUID) -> dict[str, object]:
    return get_source(source_id, custodian_id)


@app.get("/v1/sources/{source_id}/arrivals")
def get_source_arrivals(source_id: UUID, custodian_id: UUID) -> list[dict[str, object]]:
    repositories = _repositories()
    if repositories.get_source_for_custodian(source_id, custodian_id) is None:
        raise HTTPException(status_code=404, detail="Source not found.")
    return [_serialize(asdict(item)) for item in repositories.list_arrivals(source_id, custodian_id)]


@app.get("/v1/sources/{source_id}/enrollments")
def get_source_enrollments(source_id: UUID, custodian_id: UUID) -> list[dict[str, object]]:
    repositories = _repositories()
    if repositories.get_source_for_custodian(source_id, custodian_id) is None:
        raise HTTPException(status_code=404, detail="Source not found.")
    return [_serialize(asdict(item)) for item in repositories.list_enrollments(source_id, custodian_id)]


@app.get("/v1/sources/{source_id}/canonical")
def download_canonical_source(source_id: UUID, custodian_id: UUID) -> StreamingResponse:
    repositories = _repositories()
    canonical = repositories.get_canonical_for_source(source_id, custodian_id)
    if canonical is None:
        raise HTTPException(status_code=404, detail="Source not found.")
    settings = Settings.from_env()
    blob = create_blob_store(settings)
    return StreamingResponse(
        blob.iter_chunks(canonical.storage_key),
        media_type=canonical.media_type,
        headers={
            "Content-Length": str(canonical.byte_size),
            "X-Content-SHA256": canonical.sha256,
            "Content-Disposition": "attachment",
        },
    )


@app.get("/v1/custodians/{custodian_id}/sources/{source_id}/canonical")
def download_custodian_canonical_source(custodian_id: UUID, source_id: UUID) -> StreamingResponse:
    return download_canonical_source(source_id, custodian_id)


@app.get("/v1/sources/{source_id}/representations")
def list_source_representations(source_id: UUID, custodian_id: UUID) -> list[dict[str, object]]:
    repositories = _repositories()
    if repositories.get_source_for_custodian(source_id, custodian_id) is None:
        raise HTTPException(status_code=404, detail="Source not found.")
    return [_serialize(asdict(item)) for item in repositories.list_representations(source_id, custodian_id)]


@app.get("/v1/representations/{representation_id}")
def get_representation(representation_id: UUID, custodian_id: UUID) -> dict[str, object]:
    item = _repositories().get_representation(representation_id, custodian_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Derived representation not found.")
    serialized = _serialize(asdict(item))
    if not isinstance(serialized, dict):
        raise RuntimeError("Representation serialization returned a non-object.")
    return serialized


@app.get("/v1/representations/{representation_id}/download")
def download_representation(representation_id: UUID, custodian_id: UUID) -> StreamingResponse:
    item = _repositories().get_representation(representation_id, custodian_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Derived representation not found.")
    blob = create_blob_store(Settings.from_env())
    media_type = "application/json" if item.representation_kind == "page-json" else "image/png"
    return StreamingResponse(
        blob.iter_chunks(item.storage_key),
        media_type=media_type,
        headers={"Content-Length": str(item.byte_size), "X-Content-SHA256": item.content_sha256},
    )


@app.post("/extract", response_model=DocumentExtractionResponse)
async def extract(file: UploadFile = File(...)) -> DocumentExtractionResponse:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only .pdf files are accepted.")

    content = await _read_within_limit(file, MAX_UPLOAD_SIZE_BYTES)

    if not content.startswith(PDF_MAGIC):
        raise HTTPException(status_code=400, detail="Uploaded file is not a valid PDF.")

    safe_filename = Path(file.filename).name
    document_id = uuid.uuid4().hex

    try:
        result = extract_document(filename=safe_filename, pdf_bytes=content, document_id=document_id)
    except InvalidPDFError:
        raise HTTPException(
            status_code=422,
            detail="The PDF could not be processed. It may be corrupted or unsupported.",
        )

    storage.store_document(
        document_id=document_id,
        pdf_bytes=content,
        original_filename=safe_filename,
        page_count=result.page_count,
    )
    return result


@app.get("/documents/{document_id}/pages/{page_number}/image")
def get_page_image(document_id: str, page_number: int) -> Response:
    record = storage.get_document(document_id)
    if record is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found. It may have expired or never existed.",
        )

    if page_number < 1:
        raise HTTPException(status_code=400, detail="Page number must be 1 or greater.")

    if page_number > record.page_count:
        raise HTTPException(
            status_code=404,
            detail=f"Page {page_number} does not exist. This document has {record.page_count} pages.",
        )

    try:
        png_bytes, width_px, height_px, page_width_pt, page_height_pt = render_page_png(
            record.pdf_path, page_number
        )
    except PageRenderError:
        raise HTTPException(status_code=422, detail="Unable to render the requested page.")

    return Response(
        content=png_bytes,
        media_type="image/png",
        headers={
            "X-Page-Number": str(page_number),
            "X-Page-Width-Points": str(page_width_pt),
            "X-Page-Height-Points": str(page_height_pt),
            "X-Image-Width-Px": str(width_px),
            "X-Image-Height-Px": str(height_px),
            "X-Resolution-Dpi": str(DEFAULT_RESOLUTION_DPI),
        },
    )


async def _read_within_limit(file: UploadFile, max_bytes: int) -> bytes:
    chunks = []
    total = 0
    while True:
        chunk = await file.read(UPLOAD_CHUNK_SIZE)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(
                status_code=413,
                detail="File exceeds the maximum allowed upload size.",
            )
        chunks.append(chunk)
    return b"".join(chunks)


def _stream_pdf_to_stage(file: UploadFile, stage: Path, max_bytes: int) -> tuple[str, int]:
    digest = hashlib.sha256()
    header = bytearray()
    total = 0
    with stage.open("wb") as output:
        while chunk := file.file.read(UPLOAD_CHUNK_SIZE):
            total += len(chunk)
            if total > max_bytes:
                raise HTTPException(status_code=413, detail="File exceeds the maximum allowed upload size.")
            if len(header) < len(PDF_MAGIC):
                header.extend(chunk[: len(PDF_MAGIC) - len(header)])
            digest.update(chunk)
            output.write(chunk)
        output.flush()
        os.fsync(output.fileno())
    if bytes(header) != PDF_MAGIC:
        raise HTTPException(status_code=400, detail="Uploaded content is not a PDF.")
    return digest.hexdigest(), total


def _admission_fingerprint(
    *,
    sha256: str,
    byte_size: int,
    media_type: str,
    display_name: str,
    corpus_id: UUID,
    arrival_channel: str,
    claimed_origin: str,
    obtained_from: str,
) -> str:
    payload = {
        "sha256": sha256,
        "byte_size": byte_size,
        "media_type": media_type,
        "display_name": display_name,
        "corpus_id": str(corpus_id),
        "arrival_channel": arrival_channel,
        "claimed_origin": claimed_origin,
        "obtained_from": obtained_from,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _repositories() -> PostgresRepositories:
    settings = Settings.from_env()
    return PostgresRepositories(Database(settings.database_url))


def _list_sources_response(
    custodian_id: UUID, corpus_id: UUID, limit: int, offset: int
) -> dict[str, object]:
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=422, detail="limit must be between 1 and 100.")
    if offset < 0:
        raise HTTPException(status_code=422, detail="offset must be zero or greater.")
    repositories = _repositories()
    try:
        sources, total = repositories.list_sources(
            custodian_id=custodian_id, corpus_id=corpus_id, limit=limit, offset=offset
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {
        "items": [_source_response(repositories, source, custodian_id) for source in sources],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


def _source_response(
    repositories: PostgresRepositories, source: Any, custodian_id: UUID
) -> dict[str, object]:
    canonical = repositories.get_canonical_for_source(source.id, custodian_id)
    return {
        "source": _serialize(asdict(source)),
        "canonical_object": _serialize(asdict(canonical)) if canonical else None,
    }


def _iter_blob(handle: Any) -> Iterator[bytes]:
    try:
        while chunk := handle.read(UPLOAD_CHUNK_SIZE):
            yield chunk
    finally:
        handle.close()


def _serialize(value: object) -> Any:
    if isinstance(value, dict):
        return {key: _serialize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serialize(item) for item in value]
    if isinstance(value, (UUID,)):
        return str(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value
