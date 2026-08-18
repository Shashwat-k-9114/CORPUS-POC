import pytest
from fastapi.testclient import TestClient

from app import storage
from app.main import app
from tests.pdf_fixtures import valid_pdf_with_text

client = TestClient(app)


@pytest.fixture(autouse=True)
def _cleanup_documents():
    yield
    storage.clear_all()


def _extract(filename: str = "hello.pdf") -> dict:
    response = client.post(
        "/extract",
        files={"file": (filename, valid_pdf_with_text(), "application/pdf")},
    )
    assert response.status_code == 200
    return response.json()


def test_successful_extraction_creates_a_document_id():
    body = _extract()
    document_id = body["document_id"]
    assert document_id in storage.document_ids()
    record = storage.get_document(document_id)
    assert record is not None
    assert record.pdf_path.exists()
    assert record.page_count == 1


def test_valid_page_image_request_returns_200():
    document_id = _extract()["document_id"]
    response = client.get(f"/documents/{document_id}/pages/1/image")
    assert response.status_code == 200


def test_page_image_content_type_is_image():
    document_id = _extract()["document_id"]
    response = client.get(f"/documents/{document_id}/pages/1/image")
    assert response.headers["content-type"] == "image/png"
    assert response.content[:8] == b"\x89PNG\r\n\x1a\n"  # PNG magic bytes


def test_page_image_unknown_document_id_returns_404():
    response = client.get("/documents/does-not-exist/pages/1/image")
    assert response.status_code == 404


def test_page_image_invalid_page_number_returns_400():
    document_id = _extract()["document_id"]
    response = client.get(f"/documents/{document_id}/pages/0/image")
    assert response.status_code == 400


def test_page_image_out_of_range_page_number_returns_404():
    document_id = _extract()["document_id"]  # single-page fixture
    response = client.get(f"/documents/{document_id}/pages/2/image")
    assert response.status_code == 404


def test_page_image_response_headers_describe_coordinate_mapping():
    document_id = _extract()["document_id"]
    response = client.get(f"/documents/{document_id}/pages/1/image")
    page_width_pt = float(response.headers["x-page-width-points"])
    page_height_pt = float(response.headers["x-page-height-points"])
    image_width_px = int(response.headers["x-image-width-px"])
    image_height_px = int(response.headers["x-image-height-px"])
    resolution_dpi = float(response.headers["x-resolution-dpi"])

    assert page_width_pt == 200.0
    assert page_height_pt == 200.0
    # pixel = point * (resolution / 72), both axes, no separate x/y scale
    scale = resolution_dpi / 72
    assert image_width_px == pytest.approx(page_width_pt * scale, abs=1)
    assert image_height_px == pytest.approx(page_height_pt * scale, abs=1)
    # aspect ratio preserved: a square PDF page renders to a square image
    assert image_width_px == image_height_px


def test_document_cleanup_removes_expired_document(monkeypatch):
    document_id = _extract()["document_id"]
    record = storage.get_document(document_id)
    assert record is not None
    temp_dir = record.temp_dir
    assert temp_dir.exists()

    monkeypatch.setattr(storage, "DOCUMENT_TTL_SECONDS", -1)  # force immediate expiry

    assert storage.get_document(document_id) is None
    assert not temp_dir.exists()

    # the now-expired document is also gone from the image endpoint
    response = client.get(f"/documents/{document_id}/pages/1/image")
    assert response.status_code == 404
