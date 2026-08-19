# CORPUS — Requirements (v1 Prototype)

Statuses: `PROPOSED`, `PLANNED`, `IN PROGRESS`, `IMPLEMENTED`, `VALIDATED`, `REJECTED`,
`DEFERRED`.

Status column reflects actual implementation state as of the date noted per section edit
— not aspirational. See `BUILD_LOG.md` for full session-by-session detail behind each
status change.

---

## Product requirements

| ID | Requirement | Priority | Rationale | Status |
|---|---|---|---|---|
| PROD-01 | A user can upload a native-text PDF and see it processed into inspectable, page-located content. | Must | Core Corpus interaction loop for v1. | VALIDATED — full browser workflow manually tested against the real RIL PDF, Phase 5 |
| PROD-02 | A user can view the original source page image alongside extracted content for that page. | Must | Provenance is only trustworthy if the source is visibly checkable. | VALIDATED — `PageViewer` renders the page image with the region overlay side by side with `ProvenancePanel`, Phase 5 |
| PROD-03 | A user can tell where a piece of extracted text came from (page, position). | Must | Core value proposition — "finding with provenance." | VALIDATED — click-to-inspect provenance panel, manually verified on pages 22 and 81 against known-good bbox values from Phase 4 |
| PROD-04 | The application is reachable at a public URL a stakeholder can test without local setup. | Must | Explicit stakeholder requirement: "something they can see and test." | PLANNED — local only; deployment is the next task |

## Functional requirements

| ID | Requirement | Priority | Rationale | Status |
|---|---|---|---|---|
| FUNC-01 | `POST /extract` (or equivalent) accepts a PDF upload and returns structured JSON (document, pages, regions). | Must | API contract for the vertical slice. | VALIDATED |
| FUNC-02 | `GET /health` returns backend liveness status. | Must | Deployment/ops baseline, explicitly required. | VALIDATED |
| FUNC-03 | Backend renders and serves a page image for a given document + page number. | Must | Required for visual inspection (PROD-02). | VALIDATED — `GET /documents/{id}/pages/{n}/image`, verified against the real RIL PDF on pages 22 and 81, including a direct visual crop check that the mapped word coordinates land on the correct text |
| FUNC-04 | Extraction output includes page-level data: page number, dimensions, word count, char count. | Must | Required data model field (Page). | PARTIALLY IMPLEMENTED — `page_number`, `width`, `height`, `word_count` implemented and validated; `char_count` not implemented (not needed by any Phase 3 consumer yet; trivially derivable from region text later if a real need appears) |
| FUNC-05 | Extraction output includes word-level regions: text, bounding box, page number, order index. | Must | Required data model field (Region); evidence basis in `[[dec-003-extraction-engine]] `/`[[dec-005-region-granularity]]`. | VALIDATED |
| FUNC-06 | Frontend lets the user navigate between pages of an uploaded document. | Must | Required for multi-page inspection. | VALIDATED — prev/next, direct page-number entry, and page 22/81 quick jumps, Phase 5 |
| FUNC-07 | Frontend displays extracted regions for the currently viewed page. | Must | Core viewer requirement. | VALIDATED — SVG bounding-box overlay + click-to-inspect, Phase 5 |

## UX requirements

| ID | Requirement | Priority | Rationale | Status |
|---|---|---|---|---|
| UX-01 | Upload, processing, success, and error states are all visually distinct and clearly communicated. | Must | Explicit brief requirement; "do not fake successful extraction." | VALIDATED — distinct uploading/extracting/error UI, real (not simulated) phase transitions, manually verified with a real error case (non-PDF upload) |
| UX-02 | The interface communicates what document/page is currently being viewed at all times. | Must | Orientation is required for a multi-page viewer. | VALIDATED — persistent document-summary bar shows filename and current/total page at all times |
| UX-03 | The first screen presents a single, obvious primary action (upload) — not a debugging console. | Must | Brief requires "serious early-stage product," not a dev screen. | VALIDATED |
| UX-04 | Oversized or unsupported files are rejected with a clear, specific message before/without attempting extraction. | Must | Required robustness + UX behavior. | VALIDATED — manually verified live: non-PDF upload shows "Only .pdf files are accepted." (the backend's own message, unmodified) |
| UX-05 | Large documents (many pages) remain navigable without the UI becoming unresponsive. | Should | Explicit brief requirement for large files. | PARTIALLY IMPLEMENTED — the 147-page, up-to-1394-word-per-page RIL document navigated smoothly in manual testing; not load-tested against a larger document |

## Technical requirements

| ID | Requirement | Priority | Rationale | Status |
|---|---|---|---|---|
| TECH-01 | Frontend: Next.js + TypeScript. | Must | `[[dec-001-frontend-framework]]`. | ACCEPTED (decision), VALIDATED (build) — full app built and manually tested end-to-end against the live backend, Phase 5 |
| TECH-02 | Backend: Python + FastAPI. | Must | `[[dec-002-backend-framework]]`. | ACCEPTED (decision), IN PROGRESS (build) — `/health`, `/extract`, and `/documents/{id}/pages/{n}/image` implemented and validated |
| TECH-03 | Communication over HTTP/JSON only. | Must | Brief requirement; keeps frontend/backend independently replaceable. | VALIDATED |
| TECH-04 | No persistent database in v1. | Must (constraint) | `[[dec-004-no-database]]`. | ACCEPTED (decision), VALIDATED (build) — no database exists anywhere in the stack; successful uploads are retained ephemerally (temp directory, 30-min TTL, in-memory index — see `[[dec-008-ephemeral-document-retention]]`), not in any database, and are deleted, not archived, on expiry |
| TECH-05 | API response schema must not be UI-specific — structured JSON that could serve a different frontend. | Must | Explicit brief requirement (API design). | VALIDATED — `Document → Page → Region → text/bbox` shape has no UI-specific fields |

## Provenance requirements

| ID | Requirement | Priority | Rationale | Status |
|---|---|---|---|---|
| PROV-01 | Every extracted Region must carry: document, page number, bounding box, extracted text, extraction method. | Must | Explicit minimum provenance fields from brief. | VALIDATED — `page_number`, `bbox`, `text`, `extraction_method` are fields on every `Region`; document identity is carried by nesting (`Region` only ever appears inside a `DocumentExtractionResponse`), not as a repeated per-region field — a deliberate, minimal design choice, not an oversight |
| PROV-02 | Confidence values must never be invented — omit the field where the extractor does not provide one. | Must | Explicit brief instruction; pdfplumber native-text extraction has no native confidence score. | VALIDATED — `Region.confidence` is always `null`, asserted by test |
| PROV-03 | Region ordering, where available from the extractor, must be preserved and exposed (not silently discarded). | Should | Supports future reading-order/grouping work without re-extracting. | VALIDATED — `order_index` preserves pdfplumber's natural word order, asserted by test |

## Extraction requirements

| ID | Requirement | Priority | Rationale | Status |
|---|---|---|---|---|
| EXT-01 | v1 extraction engine is pdfplumber, word-level (`extract_words()`), default settings. | Must | `[[dec-003-extraction-engine]]`. | ACCEPTED (decision), VALIDATED (build) — reproduces Experiment 1's exact word counts on all 7 representative pages |
| EXT-02 | v1 does not use pdfplumber's default table detection (`find_tables()`). | Must (constraint) | Experiment 1 showed default table detection unreliable in both directions. | ACCEPTED (decision), VALIDATED (build) — `find_tables()` is not called anywhere in `app/extraction.py` |
| EXT-03 | v1 does not perform OCR of any kind. | Must (constraint) | Explicit brief instruction — scanned PDFs out of scope for v1. | ACCEPTED (decision), VALIDATED (build) |
| EXT-04 | Extraction failures on a given document/page must be surfaced, not silently swallowed into empty results. | Must | "Do not fake successful extraction." | VALIDATED — malformed PDFs return `422`, not a fake empty success; tested |

## Deployment requirements

| ID | Requirement | Priority | Rationale | Status |
|---|---|---|---|---|
| DEPLOY-01 | Frontend deployable to Vercel (or documented alternative if a strong reason emerges). | Must | Brief's preferred direction; no reason yet to deviate. | READY — `[[dec-009-prototype-deployment]]`; Vercel project setup steps documented in `DEPLOYMENT.md`, not yet executed (no account access) |
| DEPLOY-02 | Backend deployable to a simple Python hosting platform. | Must | Brief requirement; platform now chosen. | READY — `[[dec-009-prototype-deployment]]` (Render, Web Service); `backend/render.yaml` prepared but schema is externally unvalidated (no live Render docs/account access this session) — see `DEPLOYMENT.md` |
| DEPLOY-03 | No secrets committed to the repository; `.env.example` documents required environment variables. | Must | Explicit brief + general security requirement. | IMPLEMENTED — dev examples (`backend/.env.example`, `frontend/.env.example`, Phase 5) plus production placeholder examples (`backend/.env.production.example`, `frontend/.env.production.example`, Phase 6, both containing only `REPLACE-WITH-...` placeholders, no real values); no secrets exist in the app to leak |
| DEPLOY-04 | Deployed frontend and backend can communicate with each other over the public internet. | Must | Explicit acceptance criterion. | PLANNED — cannot be validated until an actual deployment exists; CORS/env-var wiring for this is prepared and documented in `DEPLOYMENT.md` §8–9 |

## Non-functional requirements

| ID | Requirement | Priority | Rationale | Status |
|---|---|---|---|---|
| NFR-01 | Uploaded file type is validated server-side (not just by file extension/UI). | Must | Security/robustness requirement. | VALIDATED — extension check + `%PDF-` magic-byte check, both server-side; tested |
| NFR-02 | Upload size is limited server-side. | Must | Security/robustness requirement. | VALIDATED — 20 MB cap enforced via chunked read, returns `413`; tested |
| NFR-03 | Uploaded filenames are sanitized before any filesystem use. | Must | Security requirement — path traversal prevention. | VALIDATED — filename reduced to its basename (`Path(name).name`) for the API response, but the client-supplied name is never used to construct any filesystem path at all: the retained file is always written as a fixed internal name (`document.pdf`) inside a server-generated `tempfile.mkdtemp()` directory (`[[dec-008-ephemeral-document-retention]]`) |
| NFR-04 | Server filesystem paths are never exposed in API responses or error messages. | Must | Security requirement. | VALIDATED — asserted by test for `/extract`; the image endpoint's error responses (`404`/`400`/`422`) are similarly static/generic and its `document_id` is never a filesystem path (dict key only, per `[[dec-008-ephemeral-document-retention]]`) |
| NFR-05 | Malformed PDFs are handled gracefully (clear error, no crash, no stack trace leaked to client). | Must | Explicit brief requirement. | VALIDATED |
| NFR-06 | Automated tests cover: health endpoint, PDF validation, extraction, page extraction, word/region extraction, malformed input, unsupported file type, empty extraction, API response structure. | Must | Explicit brief testing checklist. | VALIDATED — all nine areas covered across `test_health.py` + `test_extract.py` (13 tests total, all passing) |

## Explicit non-requirements (v1)

| ID | Non-requirement | Rationale | Status |
|---|---|---|---|
| NON-01 | OCR (any engine) | Explicit brief exclusion for v1. | REJECTED (for v1) |
| NON-02 | Marker integration | Explicit brief exclusion for v1; research still in progress in `../poc-01/`. | REJECTED (for v1) |
| NON-03 | Vector search / semantic search / RAG | Explicit brief exclusion for v1. | REJECTED (for v1) |
| NON-04 | Persistent database | No demonstrated need yet; `[[dec-004-no-database]]`. | DEFERRED |
| NON-05 | Authentication | Only add if deployment platform requires it to function. | DEFERRED |
| NON-06 | Table structure extraction | `[[dec-003-extraction-engine]]` — default detection shown unreliable in Experiment 1. | DEFERRED |
| NON-07 | Multi-tenancy, billing, enterprise observability, Kubernetes, microservices | Explicit brief exclusion; premature for a single-stakeholder prototype. | REJECTED (for v1) |
