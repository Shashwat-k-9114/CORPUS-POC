import hashlib
from io import BytesIO
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi import HTTPException, UploadFile

from app.blobstore import LocalFilesystemBlobStore
from app.main import _stream_pdf_to_stage
from tests.pdf_fixtures import non_pdf_bytes, valid_pdf_with_text


class ChunkedReader(BytesIO):
    def __init__(self, value: bytes, chunk_size: int = 7) -> None:
        super().__init__(value)
        self.chunk_size = chunk_size
        self.read_sizes: list[int] = []

    def read(self, size: int = -1) -> bytes:
        self.read_sizes.append(size)
        if size < 0:
            raise AssertionError("Admission must never request an unbounded read.")
        return super().read(min(size, self.chunk_size))


def test_admission_streams_incrementally_and_records_matching_digest(tmp_path: Path):
    content = valid_pdf_with_text()
    reader = ChunkedReader(content)
    upload = UploadFile(filename="streamed.pdf", file=reader)
    stage = LocalFilesystemBlobStore(tmp_path).stage_path("upload.part")

    digest, size = _stream_pdf_to_stage(upload, stage, max_bytes=len(content) + 1)

    assert stage.read_bytes() == content
    assert digest == hashlib.sha256(content).hexdigest()
    assert size == len(content)
    assert reader.read_sizes and all(size == 1024 * 1024 for size in reader.read_sizes)


def test_admission_rejects_non_pdf_and_staging_can_be_cleaned(tmp_path: Path):
    store = LocalFilesystemBlobStore(tmp_path)
    stage = store.stage_path("broken.part")
    upload = UploadFile(filename="broken.pdf", file=BytesIO(non_pdf_bytes()))

    with pytest.raises(HTTPException) as error:
        _stream_pdf_to_stage(upload, stage, max_bytes=1024 * 1024)
    assert error.value.status_code == 400
    stage.unlink(missing_ok=True)
    assert list(store.staging_root.glob("*.part")) == []


def test_blobstore_promotes_staging_atomically_and_leaves_no_part(tmp_path: Path):
    store = LocalFilesystemBlobStore(tmp_path)
    stage = store.stage_path("canonical.part")
    stage.write_bytes(valid_pdf_with_text())
    digest = hashlib.sha256(stage.read_bytes()).hexdigest()
    stored = store.put_canonical(uuid4(), stage, digest, stage.stat().st_size)
    assert not stage.exists()
    with store.open(stored.storage_key) as handle:
        assert handle.read() == valid_pdf_with_text()
