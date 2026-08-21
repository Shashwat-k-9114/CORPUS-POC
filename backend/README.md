# Corpus backend

FastAPI application. See root `../PROJECT.md`, `../DECISIONS.md`, `../REQUIREMENTS.md`
for product/architecture context, and `../BUILD_LOG.md` for current implementation
status. For deploying this backend (Render), see `../DEPLOYMENT.md` and
the repository-root `render.yaml` and `.env.production.example` — prepared but not
yet externally deployed.

## Durable foundation

The v0.1.0 foundation adds PostgreSQL-backed custodian, corpus, canonical object,
source, arrival, enrollment, processing-job, checkpoint, and derived-representation
records. Migrations under `migrations/` are the schema source of truth. The local
filesystem `BlobStore` keeps canonical objects and derived artifacts under separate,
custodian-scoped roots.

From `corpus-poc/`, start PostgreSQL, the migration helper, API, and separate durable worker:

```
docker compose up --build
```

The worker claims queued jobs transactionally from PostgreSQL, renews leases, processes
one page at a time, and commits page JSON/render representations with canonical lineage.
The existing `/extract` and page-image endpoints remain available for the prototype
viewer and are not replaced by the durable pipeline.

Processing monitor endpoints include `GET /v1/processing-jobs`, job detail, pages,
attempt history, retry, worker heartbeats, source representations, and custodian-bounded
derived artifact metadata/download. A lease-expired job returns to `queued`; completed
page checkpoints remain durable and are skipped by a restarted worker. Set
`CORPUS_WORKER_PAGE_DELAY_SECONDS` or `CORPUS_WORKER_FAIL_PAGE_NUMBER` only for local
failure/recovery demonstrations.

### Durable source admission

`POST /v1/admissions` (also available as `POST /v1/sources`) accepts a multipart
upload with `file`, `custodian_id`, `corpus_id`, and `arrival_channel`; `claimed_origin`
and `obtained_from` are optional. An optional `Idempotency-Key` header makes a completed
request replay-safe. The endpoint streams bytes into custodian-scoped staging,
validates the PDF header, computes SHA-256, atomically promotes canonical bytes, and
returns source, canonical object, arrival, enrollment, and queued processing-job
identities. It does not extract the document.

Read APIs require a custodian boundary: `GET /v1/sources?custodian_id=...&corpus_id=...`,
`GET /v1/sources/{source_id}?custodian_id=...`, `/arrivals`, `/enrollments`,
`/canonical`, and `GET /v1/processing-jobs/{job_id}?custodian_id=...`.

Apply migrations explicitly when needed:

```
docker compose run --rm migrate
```

`GET /health` remains a dependency-free liveness check. `GET /ready` checks the
configured PostgreSQL connection. The foundation endpoints are under `/v1/`.

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

### CORS (required for the frontend)

The frontend calls this API directly from the browser, so the backend must explicitly
allow that origin. Copy `.env.example` to `.env` and set `CORPUS_ALLOWED_ORIGINS` (a
comma-separated list) if the frontend isn't running at the default
`http://localhost:3000` / `http://127.0.0.1:3000` — for example, if that port was
already taken and Next.js picked a different one:

```
uvicorn app.main:app --reload --env-file .env
```

If this isn't set correctly, the browser will show CORS errors and the frontend's
requests will fail even though the backend is running fine — check this first if the
frontend can't reach the API.

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
  "document_id": "484ec5a9e0124b3fb79e1d4ce5cd39ee",
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

On success, the uploaded PDF is also retained server-side (temp directory, keyed by
`document_id`) for up to 30 minutes so its pages can be rendered as images — see
`DEC-004`/`DEC-008`. On failure (any `4xx`/`5xx`), nothing is retained.

**Known limitation:** extraction is fully synchronous — the request does not return
until every page has been processed. A large, complex real-world document (e.g. ~150
pages) can take over a minute. There is no progress reporting yet; see `BUILD_LOG.md`.

### `GET /documents/{document_id}/pages/{page_number}/image`

Returns a rendered PNG image of the given 1-indexed page of a previously extracted
document. `document_id` comes from a prior `POST /extract` response.

```
curl -o page.png http://127.0.0.1:8000/documents/<document_id>/pages/1/image
```

**Validation, in order:**
1. `document_id` must refer to a currently-retained document → otherwise `404`
   (covers unknown IDs, malformed IDs, and expired documents identically — the API does
   not distinguish "never existed" from "expired" in its response).
2. `page_number` must be `>= 1` → otherwise `400`.
3. `page_number` must be `<=` the document's page count → otherwise `404`.
4. The page must actually render → otherwise `422`, generic message, no internals or
   paths leaked.

**Response:** `image/png` bytes, plus headers that make the coordinate mapping
explicit:

| Header | Meaning |
|---|---|
| `X-Page-Number` | The 1-indexed page rendered |
| `X-Page-Width-Points` / `X-Page-Height-Points` | Same units as `POST /extract`'s `pages[].width`/`.height` and every `bbox` field |
| `X-Image-Width-Px` / `X-Image-Height-Px` | Pixel dimensions of the returned PNG |
| `X-Resolution-Dpi` | Rendering resolution used (currently fixed at 150 DPI — matches `../poc-01/scripts/render_pages.py`'s default; explicitly not 300 DPI, so images stay a reasonable size for a browser) |

**Coordinate-system relationship (explicit, load-bearing):** pdfplumber's word bounding
boxes (from `POST /extract`) and the page's `width`/`height` are in PDF points, origin
at the page's top-left corner, `top`/`bottom` increasing downward. The rendered image
uses that exact same top-left-origin space, scaled uniformly by `resolution / 72` on
both axes — i.e. `pixel_x = point_x * (resolution / 72)` and `pixel_y = point_y *
(resolution / 72)`. There is no vertical flip and no separate x/y scale factor, so
aspect ratio is preserved automatically. A future frontend can map any `bbox` from
`POST /extract` directly onto the image returned here using only the headers above (no
hardcoded DPI needed, though it currently is fixed). This mapping was verified manually
against the real RIL PDF (see `BUILD_LOG.md`, Phase 4) by cropping the image at a word's
mapped pixel coordinates and visually confirming the correct word appears there.
