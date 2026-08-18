from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.extraction import InvalidPDFError, extract_document
from app.models import DocumentExtractionResponse

app = FastAPI(title="Corpus API", version="0.1.0")

MAX_UPLOAD_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB
PDF_MAGIC = b"%PDF-"
UPLOAD_CHUNK_SIZE = 1024 * 1024  # 1 MB


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

    try:
        return extract_document(filename=safe_filename, pdf_bytes=content)
    except InvalidPDFError:
        raise HTTPException(
            status_code=422,
            detail="The PDF could not be processed. It may be corrupted or unsupported.",
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
