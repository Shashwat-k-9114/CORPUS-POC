import app.main as main_module
from fastapi.testclient import TestClient

from app.main import app
from tests.pdf_fixtures import (
    blank_page_pdf,
    malformed_pdf_bytes,
    non_pdf_bytes,
    valid_pdf_with_text,
)

client = TestClient(app)


def _upload(filename: str, content: bytes, content_type: str = "application/pdf"):
    return client.post(
        "/extract",
        files={"file": (filename, content, content_type)},
    )


def test_extract_valid_pdf_returns_200():
    response = _upload("hello.pdf", valid_pdf_with_text())
    assert response.status_code == 200


def test_extract_response_has_expected_top_level_structure():
    response = _upload("hello.pdf", valid_pdf_with_text())
    body = response.json()
    assert body["filename"] == "hello.pdf"
    assert body["page_count"] == 1
    assert body["extraction_method"] == "pdfplumber_extract_words"
    assert "extraction_engine_version" in body
    assert isinstance(body["pages"], list)
    assert len(body["pages"]) == 1


def test_extract_page_metadata_is_correct():
    response = _upload("hello.pdf", valid_pdf_with_text())
    page = response.json()["pages"][0]
    assert page["page_number"] == 1
    assert page["width"] == 200
    assert page["height"] == 200
    assert page["word_count"] == 2
    assert len(page["regions"]) == 2


def test_extract_region_text_matches_words():
    response = _upload("hello.pdf", valid_pdf_with_text())
    regions = response.json()["pages"][0]["regions"]
    texts = [r["text"] for r in regions]
    assert texts == ["Hello", "World"]


def test_extract_region_bounding_boxes_and_order_are_present():
    response = _upload("hello.pdf", valid_pdf_with_text())
    regions = response.json()["pages"][0]["regions"]
    for i, region in enumerate(regions):
        assert region["page_number"] == 1
        assert region["order_index"] == i
        assert region["extraction_method"] == "pdfplumber_extract_words"
        assert region["confidence"] is None
        bbox = region["bbox"]
        assert bbox["x0"] < bbox["x1"]
        assert bbox["top"] < bbox["bottom"]
    # "Hello" appears before "World" left-to-right
    assert regions[0]["bbox"]["x0"] < regions[1]["bbox"]["x0"]


def test_extract_blank_page_pdf_returns_empty_regions():
    response = _upload("blank.pdf", blank_page_pdf())
    assert response.status_code == 200
    page = response.json()["pages"][0]
    assert page["word_count"] == 0
    assert page["regions"] == []


def test_extract_rejects_non_pdf_extension():
    response = _upload("notes.txt", non_pdf_bytes(), content_type="text/plain")
    assert response.status_code == 400
    assert ".pdf" in response.json()["detail"].lower() or "pdf" in response.json()["detail"].lower()


def test_extract_rejects_content_that_is_not_actually_pdf():
    response = _upload("fake.pdf", non_pdf_bytes())
    assert response.status_code == 400


def test_extract_rejects_malformed_pdf():
    response = _upload("broken.pdf", malformed_pdf_bytes())
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert "\\" not in detail and "/" not in detail.replace("PDF", "")


def test_extract_error_responses_do_not_leak_internal_details():
    response = _upload("broken.pdf", malformed_pdf_bytes())
    detail = response.json()["detail"]
    assert "Traceback" not in detail
    assert "pdfminer" not in detail.lower()
    assert "C:\\" not in detail


def test_extract_rejects_oversized_upload(monkeypatch):
    monkeypatch.setattr(main_module, "MAX_UPLOAD_SIZE_BYTES", 10)
    response = _upload("hello.pdf", valid_pdf_with_text())
    assert response.status_code == 413
