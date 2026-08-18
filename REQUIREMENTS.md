# CORPUS — Requirements (v1 Prototype)

Statuses: `PROPOSED`, `PLANNED`, `IN PROGRESS`, `IMPLEMENTED`, `VALIDATED`, `REJECTED`,
`DEFERRED`.

All requirements below are `PLANNED` unless stated otherwise — no application code has
been written yet as of this document's creation (Phase 0/1, 2026-08-18).

---

## Product requirements

| ID | Requirement | Priority | Rationale | Status |
|---|---|---|---|---|
| PROD-01 | A user can upload a native-text PDF and see it processed into inspectable, page-located content. | Must | Core Corpus interaction loop for v1. | PLANNED |
| PROD-02 | A user can view the original source page image alongside extracted content for that page. | Must | Provenance is only trustworthy if the source is visibly checkable. | PLANNED |
| PROD-03 | A user can tell where a piece of extracted text came from (page, position). | Must | Core value proposition — "finding with provenance." | PLANNED |
| PROD-04 | The application is reachable at a public URL a stakeholder can test without local setup. | Must | Explicit stakeholder requirement: "something they can see and test." | PLANNED |

## Functional requirements

| ID | Requirement | Priority | Rationale | Status |
|---|---|---|---|---|
| FUNC-01 | `POST /extract` (or equivalent) accepts a PDF upload and returns structured JSON (document, pages, regions). | Must | API contract for the vertical slice. | PLANNED |
| FUNC-02 | `GET /health` returns backend liveness status. | Must | Deployment/ops baseline, explicitly required. | PLANNED |
| FUNC-03 | Backend renders and serves a page image for a given document + page number. | Must | Required for visual inspection (PROD-02). | PLANNED |
| FUNC-04 | Extraction output includes page-level data: page number, dimensions, word count, char count. | Must | Required data model field (Page). | PLANNED |
| FUNC-05 | Extraction output includes word-level regions: text, bounding box, page number, order index. | Must | Required data model field (Region); evidence basis in `[[dec-003-extraction-engine]] `/`[[dec-005-region-granularity]]`. | PLANNED |
| FUNC-06 | Frontend lets the user navigate between pages of an uploaded document. | Must | Required for multi-page inspection. | PLANNED |
| FUNC-07 | Frontend displays extracted regions for the currently viewed page. | Must | Core viewer requirement. | PLANNED |

## UX requirements

| ID | Requirement | Priority | Rationale | Status |
|---|---|---|---|---|
| UX-01 | Upload, processing, success, and error states are all visually distinct and clearly communicated. | Must | Explicit brief requirement; "do not fake successful extraction." | PLANNED |
| UX-02 | The interface communicates what document/page is currently being viewed at all times. | Must | Orientation is required for a multi-page viewer. | PLANNED |
| UX-03 | The first screen presents a single, obvious primary action (upload) — not a debugging console. | Must | Brief requires "serious early-stage product," not a dev screen. | PLANNED |
| UX-04 | Oversized or unsupported files are rejected with a clear, specific message before/without attempting extraction. | Must | Required robustness + UX behavior. | PLANNED |
| UX-05 | Large documents (many pages) remain navigable without the UI becoming unresponsive. | Should | Explicit brief requirement for large files. | PLANNED |

## Technical requirements

| ID | Requirement | Priority | Rationale | Status |
|---|---|---|---|---|
| TECH-01 | Frontend: Next.js + TypeScript. | Must | `[[dec-001-frontend-framework]]`. | ACCEPTED (decision), PLANNED (build) |
| TECH-02 | Backend: Python + FastAPI. | Must | `[[dec-002-backend-framework]]`. | ACCEPTED (decision), PLANNED (build) |
| TECH-03 | Communication over HTTP/JSON only. | Must | Brief requirement; keeps frontend/backend independently replaceable. | PLANNED |
| TECH-04 | No persistent database in v1. | Must (constraint) | `[[dec-004-no-database]]`. | ACCEPTED (decision) |
| TECH-05 | API response schema must not be UI-specific — structured JSON that could serve a different frontend. | Must | Explicit brief requirement (API design). | PLANNED |

## Provenance requirements

| ID | Requirement | Priority | Rationale | Status |
|---|---|---|---|---|
| PROV-01 | Every extracted Region must carry: document, page number, bounding box, extracted text, extraction method. | Must | Explicit minimum provenance fields from brief. | PLANNED |
| PROV-02 | Confidence values must never be invented — omit the field where the extractor does not provide one. | Must | Explicit brief instruction; pdfplumber native-text extraction has no native confidence score. | PLANNED |
| PROV-03 | Region ordering, where available from the extractor, must be preserved and exposed (not silently discarded). | Should | Supports future reading-order/grouping work without re-extracting. | PLANNED |

## Extraction requirements

| ID | Requirement | Priority | Rationale | Status |
|---|---|---|---|---|
| EXT-01 | v1 extraction engine is pdfplumber, word-level (`extract_words()`), default settings. | Must | `[[dec-003-extraction-engine]]`. | ACCEPTED (decision) |
| EXT-02 | v1 does not use pdfplumber's default table detection (`find_tables()`). | Must (constraint) | Experiment 1 showed default table detection unreliable in both directions. | ACCEPTED (decision) |
| EXT-03 | v1 does not perform OCR of any kind. | Must (constraint) | Explicit brief instruction — scanned PDFs out of scope for v1. | ACCEPTED (decision) |
| EXT-04 | Extraction failures on a given document/page must be surfaced, not silently swallowed into empty results. | Must | "Do not fake successful extraction." | PLANNED |

## Deployment requirements

| ID | Requirement | Priority | Rationale | Status |
|---|---|---|---|---|
| DEPLOY-01 | Frontend deployable to Vercel (or documented alternative if a strong reason emerges). | Must | Brief's preferred direction; no reason yet to deviate. | PLANNED |
| DEPLOY-02 | Backend deployable to a simple Python hosting platform. | Must | Brief requirement; specific platform is an open question (`[[dec-007-test-fixture-source]]` area, see DECISIONS.md open questions). | PLANNED |
| DEPLOY-03 | No secrets committed to the repository; `.env.example` documents required environment variables. | Must | Explicit brief + general security requirement. | PLANNED |
| DEPLOY-04 | Deployed frontend and backend can communicate with each other over the public internet. | Must | Explicit acceptance criterion. | PLANNED |

## Non-functional requirements

| ID | Requirement | Priority | Rationale | Status |
|---|---|---|---|---|
| NFR-01 | Uploaded file type is validated server-side (not just by file extension/UI). | Must | Security/robustness requirement. | PLANNED |
| NFR-02 | Upload size is limited server-side. | Must | Security/robustness requirement. | PLANNED |
| NFR-03 | Uploaded filenames are sanitized before any filesystem use. | Must | Security requirement — path traversal prevention. | PLANNED |
| NFR-04 | Server filesystem paths are never exposed in API responses or error messages. | Must | Security requirement. | PLANNED |
| NFR-05 | Malformed PDFs are handled gracefully (clear error, no crash, no stack trace leaked to client). | Must | Explicit brief requirement. | PLANNED |
| NFR-06 | Automated tests cover: health endpoint, PDF validation, extraction, page extraction, word/region extraction, malformed input, unsupported file type, empty extraction, API response structure. | Must | Explicit brief testing checklist. | PLANNED |

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
