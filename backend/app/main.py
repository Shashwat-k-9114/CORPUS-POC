import os
import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

from app import storage
from app.extraction import InvalidPDFError, extract_document
from app.models import DocumentExtractionResponse
from app.rendering import DEFAULT_RESOLUTION_DPI, PageRenderError, render_page_png

app = FastAPI(title="Corpus API", version="0.1.0")

MAX_UPLOAD_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB
PDF_MAGIC = b"%PDF-"
UPLOAD_CHUNK_SIZE = 1024 * 1024  # 1 MB

# CORS: the frontend (Next.js, a different origin) calls this API directly from the
# browser and must read the coordinate-mapping headers off the image response, which
# requires an explicit allow-list and expose_headers (see BUILD_LOG.md, Phase 5).
DEFAULT_ALLOWED_ORIGINS = "http://localhost:3000,http://127.0.0.1:3000"
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


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="corpus-backend", version=app.version)


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
