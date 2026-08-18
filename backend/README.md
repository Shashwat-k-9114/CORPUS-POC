# Corpus backend

FastAPI application. See root `../PROJECT.md`, `../DECISIONS.md`, `../REQUIREMENTS.md`
for product/architecture context, and `../BUILD_LOG.md` for current implementation
status.

## Setup

```
python -m venv .venv
.venv\Scripts\activate       # Windows
pip install -r requirements.txt
```

## Run (development)

```
uvicorn app.main:app --reload
```

Serves on `http://127.0.0.1:8000`. Interactive API docs at `/docs`.

## Test

```
pytest
```

## API

### `GET /health`

Liveness check. Returns `{"status": "ok", "service": "corpus-backend", "version": "..."}`.

### `POST /extract`

Accepts exactly one PDF upload (`multipart/form-data`, field name `file`) and returns
word-level extraction with bounding boxes for every page.

```
curl -X POST http://127.0.0.1:8000/extract -F "file=@/path/to/document.pdf"
```

**Validation, in order:**
1. Filename must end in `.pdf` → otherwise `400`.
2. Upload must not exceed 20 MB (streamed in 1 MB chunks, rejected as soon as the limit
   is crossed) → otherwise `413`.
3. File content must start with the `%PDF-` magic bytes → otherwise `400`.
4. The file must actually open and parse with pdfplumber → otherwise `422`. Error
   messages are generic; they never include a stack trace or a server filesystem path.

**Response shape** (`Document → Page → Region → text + bbox`):

```json
{
  "filename": "document.pdf",
  "page_count": 1,
  "extraction_method": "pdfplumber_extract_words",
  "extraction_engine_version": "0.11.10",
  "pages": [
    {
      "page_number": 1,
      "width": 200.0,
      "height": 200.0,
      "word_count": 2,
      "regions": [
        {
          "text": "Hello",
          "bbox": { "x0": 20.0, "x1": 74.67, "top": 80.97, "bottom": 104.97 },
          "page_number": 1,
          "order_index": 0,
          "extraction_method": "pdfplumber_extract_words",
          "confidence": null
        }
      ]
    }
  ]
}
```

`confidence` is always `null` in v1 — pdfplumber's native text extraction has no
confidence signal, and this API never fabricates one (see `REQUIREMENTS.md` PROV-02).
Bounding-box units are PDF points, in pdfplumber's coordinate convention (`top`/`bottom`
measured from the top of the page, not PDF's native bottom-up y-axis).

**Known limitation:** extraction is fully synchronous — the request does not return
until every page has been processed. A large, complex real-world document (e.g. ~150
pages) can take over a minute. There is no progress reporting yet; see `BUILD_LOG.md`.
