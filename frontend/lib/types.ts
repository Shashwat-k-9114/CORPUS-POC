// Mirrors backend/app/models.py exactly. Keep in sync by hand -- there is no
// schema-generation step in this prototype (see DECISIONS.md if that changes).

export interface BoundingBox {
  x0: number;
  x1: number;
  top: number;
  bottom: number;
}

export interface Region {
  text: string;
  bbox: BoundingBox;
  page_number: number;
  order_index: number;
  extraction_method: string;
  confidence: number | null;
}

export interface PageExtraction {
  page_number: number;
  width: number;
  height: number;
  word_count: number;
  regions: Region[];
}

export interface DocumentExtractionResponse {
  document_id: string;
  filename: string;
  page_count: number;
  extraction_method: string;
  extraction_engine_version: string;
  pages: PageExtraction[];
}
