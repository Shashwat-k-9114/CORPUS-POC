import io

import pytest

from app.processor import DocumentProcessingError, PageProcessingError, open_pdf, process_page
from tests.pdf_fixtures import build_multi_page_pdf


def test_page_processor_keeps_page_contract_and_returns_one_page_artifacts() -> None:
    pdf_bytes = build_multi_page_pdf(2)
    with open_pdf(io.BytesIO(pdf_bytes)) as pdf:
        first = process_page(pdf, 1)
        second = process_page(pdf, 2)

    assert first.page.page_number == 1
    assert first.page.word_count == 2
    assert first.page.regions[0].bbox.top >= 0
    assert first.render_bytes.startswith(b"\x89PNG")
    assert b'"page_number":1' in first.json_bytes
    assert second.page.page_number == 2
    assert second.json_bytes != first.json_bytes


def test_invalid_pdf_is_classified_as_document_failure() -> None:
    with pytest.raises(DocumentProcessingError):
        open_pdf(io.BytesIO(b"%PDF-1.4\nnot a PDF\n%%EOF"))


def test_page_failure_is_typed() -> None:
    with open_pdf(io.BytesIO(build_multi_page_pdf(1))) as pdf:
        with pytest.raises(PageProcessingError):
            process_page(pdf, 2)
