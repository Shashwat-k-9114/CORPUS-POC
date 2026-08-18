import io

import pdfplumber

from app.models import BoundingBox, DocumentExtractionResponse, PageExtraction, Region

EXTRACTION_METHOD = "pdfplumber_extract_words"


class InvalidPDFError(Exception):
    pass


def extract_document(filename: str, pdf_bytes: bytes, document_id: str) -> DocumentExtractionResponse:
    try:
        pdf = pdfplumber.open(io.BytesIO(pdf_bytes))
    except Exception as exc:
        raise InvalidPDFError("Unable to open uploaded file as a PDF.") from exc

    try:
        pages: list[PageExtraction] = []
        for page_index, page in enumerate(pdf.pages):
            page_number = page_index + 1
            words = page.extract_words(use_text_flow=False, keep_blank_chars=False)
            regions = [
                Region(
                    text=word["text"],
                    bbox=BoundingBox(
                        x0=round(word["x0"], 2),
                        x1=round(word["x1"], 2),
                        top=round(word["top"], 2),
                        bottom=round(word["bottom"], 2),
                    ),
                    page_number=page_number,
                    order_index=order_index,
                    extraction_method=EXTRACTION_METHOD,
                )
                for order_index, word in enumerate(words)
            ]
            pages.append(
                PageExtraction(
                    page_number=page_number,
                    width=round(page.width, 2),
                    height=round(page.height, 2),
                    word_count=len(regions),
                    regions=regions,
                )
            )
    except Exception as exc:
        raise InvalidPDFError("Unable to extract content from the uploaded PDF.") from exc
    finally:
        pdf.close()

    return DocumentExtractionResponse(
        document_id=document_id,
        filename=filename,
        page_count=len(pages),
        extraction_method=EXTRACTION_METHOD,
        extraction_engine_version=pdfplumber.__version__,
        pages=pages,
    )
