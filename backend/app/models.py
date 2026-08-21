from pydantic import BaseModel


class BoundingBox(BaseModel):
    x0: float
    x1: float
    top: float
    bottom: float


class Region(BaseModel):
    text: str
    bbox: BoundingBox
    page_number: int
    order_index: int
    extraction_method: str
    confidence: float | None = None


class PageExtraction(BaseModel):
    page_number: int
    width: float
    height: float
    word_count: int
    regions: list[Region]


class DocumentExtractionResponse(BaseModel):
    document_id: str
    filename: str
    page_count: int
    extraction_method: str
    extraction_engine_version: str
    pages: list[PageExtraction]
