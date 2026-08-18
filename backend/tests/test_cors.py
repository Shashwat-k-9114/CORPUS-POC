import pytest
from fastapi.testclient import TestClient

from app import storage
from app.main import app
from tests.pdf_fixtures import valid_pdf_with_text

client = TestClient(app)

FRONTEND_ORIGIN = "http://localhost:3000"


@pytest.fixture(autouse=True)
def _cleanup_documents():
    yield
    storage.clear_all()


def test_health_allows_the_configured_frontend_origin():
    response = client.get("/health", headers={"Origin": FRONTEND_ORIGIN})
    assert response.headers.get("access-control-allow-origin") == FRONTEND_ORIGIN


def test_disallowed_origin_is_not_echoed_back():
    response = client.get("/health", headers={"Origin": "http://evil.example.com"})
    assert response.headers.get("access-control-allow-origin") != "http://evil.example.com"


def test_page_image_exposes_coordinate_headers_via_cors():
    extract_response = client.post(
        "/extract",
        files={"file": ("hello.pdf", valid_pdf_with_text(), "application/pdf")},
    )
    document_id = extract_response.json()["document_id"]

    response = client.get(
        f"/documents/{document_id}/pages/1/image",
        headers={"Origin": FRONTEND_ORIGIN},
    )
    assert response.status_code == 200
    exposed = response.headers.get("access-control-expose-headers", "")
    for header_name in [
        "X-Page-Width-Points",
        "X-Page-Height-Points",
        "X-Image-Width-Px",
        "X-Image-Height-Px",
        "X-Resolution-Dpi",
    ]:
        assert header_name in exposed
