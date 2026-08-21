"""Bounded-memory, one-page-at-a-time PDF processing primitives."""

from __future__ import annotations

import gc
import io
import json
from dataclasses import dataclass
from typing import Any

import pdfplumber

from app.extraction import EXTRACTION_METHOD
from app.models import BoundingBox, PageExtraction, Region
from app.rendering import DEFAULT_RESOLUTION_DPI


class DocumentProcessingError(Exception):
    """A document cannot be opened or inspected as a supported PDF."""


class PageProcessingError(Exception):
    """A single page could not be extracted or rendered."""


@dataclass(frozen=True)
class ProcessedPage:
    page: PageExtraction
    render_bytes: bytes
    image_width_px: int
    image_height_px: int

    @property
    def json_bytes(self) -> bytes:
        return (json.dumps(self.page.model_dump(exclude_none=True), separators=(",", ":")) + "\n").encode("utf-8")


def open_pdf(stream: Any) -> Any:
    try:
        return pdfplumber.open(stream)
    except Exception as exc:
        raise DocumentProcessingError("Unable to open the canonical object as a PDF.") from exc


def process_page(pdf: Any, page_number: int, resolution: int = DEFAULT_RESOLUTION_DPI) -> ProcessedPage:
    try:
        page = pdf.pages[page_number - 1]
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
        page_extraction = PageExtraction(
            page_number=page_number,
            width=round(page.width, 2),
            height=round(page.height, 2),
            word_count=len(regions),
            regions=regions,
        )
        page_image = page.to_image(resolution=resolution)
        buffer = io.BytesIO()
        page_image.original.save(buffer, format="PNG")
        width_px, height_px = page_image.original.size
        render_bytes = buffer.getvalue()
        del page_image
        del buffer
        result = ProcessedPage(page_extraction, render_bytes, width_px, height_px)
        page.flush_cache()
        gc.collect()
        return result
    except Exception as exc:
        raise PageProcessingError(f"Unable to process page {page_number}.") from exc
