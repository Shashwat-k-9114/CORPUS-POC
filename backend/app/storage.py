import atexit
import shutil
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

DOCUMENT_TTL_SECONDS = 30 * 60  # 30 minutes


@dataclass
class DocumentRecord:
    document_id: str
    pdf_path: Path
    temp_dir: Path
    original_filename: str
    page_count: int
    created_at: float


_documents: dict[str, DocumentRecord] = {}


def store_document(document_id: str, pdf_bytes: bytes, original_filename: str, page_count: int) -> None:
    """Persist an already-extracted PDF to a fresh temp directory, keyed by document_id.

    document_id is caller-generated (never derived from the original filename) and is
    used only as a dict key here -- it is never concatenated into a filesystem path, so
    an unrecognized or malicious document_id cannot reach the filesystem at all.
    """
    _sweep_expired()
    temp_dir = Path(tempfile.mkdtemp(prefix="corpus_doc_"))
    pdf_path = temp_dir / "document.pdf"
    pdf_path.write_bytes(pdf_bytes)
    _documents[document_id] = DocumentRecord(
        document_id=document_id,
        pdf_path=pdf_path,
        temp_dir=temp_dir,
        original_filename=original_filename,
        page_count=page_count,
        created_at=time.time(),
    )


def get_document(document_id: str) -> DocumentRecord | None:
    _sweep_expired()
    return _documents.get(document_id)


def document_ids() -> list[str]:
    """Test/introspection helper -- not exposed via the API."""
    return list(_documents.keys())


def clear_all() -> None:
    """Evict every retained document and delete its temp directory. Used by tests and
    registered as an atexit hook so a normal process exit doesn't leave orphaned temp
    directories behind."""
    for doc_id in list(_documents.keys()):
        _evict(doc_id)


def _sweep_expired(now: float | None = None) -> None:
    now = time.time() if now is None else now
    expired_ids = [
        doc_id
        for doc_id, record in _documents.items()
        if now - record.created_at > DOCUMENT_TTL_SECONDS
    ]
    for doc_id in expired_ids:
        _evict(doc_id)


def _evict(document_id: str) -> None:
    record = _documents.pop(document_id, None)
    if record is not None:
        shutil.rmtree(record.temp_dir, ignore_errors=True)


atexit.register(clear_all)
