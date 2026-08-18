# CORPUS — Build Log

Living record of what has actually been built or changed, session by session, most
recent first. This is factual, not aspirational — statuses are one of `IMPLEMENTED`,
`PARTIALLY IMPLEMENTED`, `NOT IMPLEMENTED`, `KNOWN ISSUE`.

---

## 2026-08-18 — Phase 0/1: Repository inspection, planning, documentation foundation

**Task:** Inspect the existing (empty) `corpus-poc` scaffold and the read-only research
in `../poc-01/`, establish the repository foundation, and create the four living project
documents plus README, before any application code is written.

**What was built:**
- Inspected `corpus-poc/`: found an empty `.gitignore`, empty `README.md`, and empty
  `backend/` and `frontend/` directories already present. No git repository existed yet.
- Inspected `../poc-01/`: reviewed `reports/experiment_01_summary.md` (pdfplumber
  baseline on the RIL Integrated Annual Report 2025-26, 147 pages, native text PDF) and
  `scripts/extract_pdfplumber.py` (the actual extraction code/output schema used), and
  sampled `outputs/2026-08-17_pdfplumber_RIL_IAR_2026/inspection.json` for page geometry
  (pages are 1190.55 × 841.89 pt — two-page spreads — except covers).
- Wrote `.gitignore` (Python/Node/Next.js caches, `.env*`, uploads/tmp dirs, `*.pdf`
  blanket-excluded, OS/editor cruft, logs).
- Wrote `PROJECT.md` (product purpose, v1 scope, explicit out-of-scope list, target
  stakeholder, current user journey, roadmap, current status).
- Wrote `REQUIREMENTS.md` (Product, Functional, UX, Technical, Provenance, Extraction,
  Deployment, Non-functional requirements, and explicit non-requirements — all IDed and
  statused, all currently `PLANNED` except the decisions already made).
- Wrote `DECISIONS.md` with seven initial decisions (DEC-001 through DEC-007): Next.js +
  TypeScript frontend, FastAPI backend, pdfplumber word-level-only extraction for v1,
  no persistent database, word-level region granularity, single monorepo structure, and
  read-only in-place reference to the `../poc-01/` RIL PDF as the test document (never
  copied into this repo). Two open questions logged (backend hosting platform; whether a
  small CI-only fixture PDF is needed later).
- This file (`BUILD_LOG.md`).

**Files added/modified:**
- `.gitignore` (was empty, now populated)
- `PROJECT.md` (new)
- `REQUIREMENTS.md` (new)
- `DECISIONS.md` (new)
- `BUILD_LOG.md` (new, this file)
- `README.md` (populated — see below)

**Behaviour added/changed:** None — no application code exists yet. This session is
documentation and repository foundation only.

**Tests performed:** None applicable — no code to test yet.

**Deployment status:** NOT IMPLEMENTED. No deployment has been attempted.

**Known issues:** None yet identified (nothing built yet to have issues).

**Next immediate task:** Initialize git and make the first commit (repository
foundation). Then begin Phase 2 (minimal backend): a FastAPI app with `GET /health` only,
run locally, verified with a manual request — the smallest possible slice before adding
extraction logic.

---

## 2026-08-18 — Phase 2: Minimal FastAPI backend (`GET /health` only)

**Task:** Build the smallest possible backend vertical slice — a FastAPI app exposing
only `GET /health`, with dependency configuration, a run/dev workflow, and an automated
test. No extraction logic, no frontend.

**What was built:**
- `backend/app/main.py` — FastAPI app (`title="Corpus API"`, `version="0.1.0"`) with a
  single `GET /health` route returning a Pydantic-modeled JSON body:
  `{"status": "ok", "service": "corpus-backend", "version": "0.1.0"}`.
- `backend/app/__init__.py` — makes `app` a package.
- `backend/conftest.py` — empty, present so pytest adds `backend/` to `sys.path`,
  allowing `tests/` to `import app.main` without packaging the app.
- `backend/tests/test_health.py` — two tests: status code is 200, and the response body
  has the expected `status`/`service`/`version` fields.
- `backend/requirements.txt` — pinned dependency list (see below for version note).
- `backend/README.md` — setup/run/test instructions (venv, `pip install -r
  requirements.txt`, `uvicorn app.main:app --reload`, `pytest`).
- `backend/.venv/` — local virtual environment created and populated (gitignored, not
  committed).

**Dependency note (environment-driven, not a product decision):** The local interpreter
is Python 3.14.6. The originally-planned pinned versions (fastapi 0.115.6 / pydantic
2.10.4 / uvicorn 0.34.0) do not have prebuilt wheels for cp314 and pydantic-core failed
to build from source (PyO3 does not yet support 3.14). Resolved by installing current
compatible releases instead: `fastapi==0.141.1`, `pydantic==2.13.4`,
`uvicorn[standard]==0.52.3`, `pytest==9.1.1`, `httpx==0.28.1`. `requirements.txt` was
updated to match what is actually installed and verified working. This is a routine
environment-compatibility fix, not judged to warrant a DECISIONS.md entry (no
alternative framework/library was considered — same libraries, newer versions).

**Files added/modified:**
- `backend/app/__init__.py` (new)
- `backend/app/main.py` (new)
- `backend/conftest.py` (new)
- `backend/tests/test_health.py` (new)
- `backend/requirements.txt` (new, then corrected to working pinned versions)
- `backend/README.md` (new)
- `backend/.venv/` (new, local only, not committed — see `.gitignore`)

**Behaviour added/changed:** Backend now runs and serves one real endpoint,
`GET /health`, returning structured JSON. No extraction, upload, or document behavior
exists yet.

**Tests performed:**
- `pytest -v` in `backend/`: 2 passed, 0 failed (`test_health_returns_200`,
  `test_health_returns_expected_structure`). One non-blocking deprecation warning noted
  below.
- Manual verification: started `uvicorn app.main:app` locally, confirmed with `curl -i
  http://127.0.0.1:8000/health` → `HTTP/1.1 200 OK`, body
  `{"status":"ok","service":"corpus-backend","version":"0.1.0"}`. Also confirmed
  `/docs` (auto-generated OpenAPI UI) returns `200`. Server was then stopped cleanly and
  a follow-up request confirmed it was no longer reachable.

**Deployment status:** NOT IMPLEMENTED. Local only, per Phase 2 scope.

**Known issues:**
- `StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated;
  install httpx2 instead` — surfaced by the very recent Starlette 1.6.0 pulled in by
  fastapi 0.141.1. Tests pass; this is a future dependency-maintenance item, not a
  functional defect. Not fixed now to keep this phase minimal.
- No `.env.example` yet — correct, since no environment variables exist in this phase
  (health check has no config). Will be added when the first real environment variable
  is introduced (expected in Phase 2 continuation / Phase 4, e.g. upload size limits).

**Next immediate task:** Begin PDF upload/extraction work (`POST /extract` with
pdfplumber word-level regions, per `DEC-003`/`DEC-005`) as its own phase — not started in
this session.

---

## 2026-08-18 — Phase 3: PDF extraction API (`POST /extract`)

**Task:** Build the smallest complete vertical slice for PDF upload → validation →
pdfplumber word-level extraction → structured JSON, per `DEC-003`/`DEC-005`. No frontend,
no deployment, no persistent storage.

**What was built:**
- `backend/app/models.py` — `BoundingBox`, `Region` (`text`, `bbox`, `page_number`,
  `order_index`, `extraction_method`, `confidence: Optional[float] = None`),
  `PageExtraction` (`page_number`, `width`, `height`, `word_count`, `regions`),
  `DocumentExtractionResponse` (`filename`, `page_count`, `extraction_method`,
  `extraction_engine_version`, `pages`). Shape is `Document → Page → Region → text+bbox`
  as specified.
- `backend/app/extraction.py` — `extract_document(filename, pdf_bytes)`. Opens the PDF
  from an in-memory `io.BytesIO` buffer (never written to disk — see storage note
  below), iterates `pdf.pages`, and calls `page.extract_words(use_text_flow=False,
  keep_blank_chars=False)` per page — the exact same call signature Experiment 1 used
  (`../poc-01/scripts/extract_pdfplumber.py`), so results are directly comparable to
  the existing research. Does not call `extract_text()` or `find_tables()`. Any
  exception during open or extraction is wrapped as `InvalidPDFError` (internal
  exception details are never propagated to the HTTP layer).
- `backend/app/main.py` — added `POST /extract` (`UploadFile`, field name `file`):
  validates extension → reads upload in 1 MB chunks capped at
  `MAX_UPLOAD_SIZE_BYTES = 20 * 1024 * 1024` (413 if exceeded) → checks the `%PDF-`
  magic bytes (400 if absent) → sanitizes the filename to its basename
  (`Path(name).name`) before use → calls `extract_document` (422 on `InvalidPDFError`,
  generic message, no internals leaked).
- `backend/tests/pdf_fixtures.py` — a hand-built, dependency-free minimal-PDF byte
  generator (`build_minimal_pdf`) used to produce four deterministic fixtures at test
  time: a valid one-page PDF containing "Hello World", a valid PDF with a blank/empty
  content stream, a `%PDF-`-prefixed-but-malformed byte string, and plain non-PDF bytes.
  No binary files committed to the repo.
- `backend/tests/test_extract.py` — 11 tests (see below).
- Added `pdfplumber==0.11.10` (same version Experiment 1 used) and
  `python-multipart==0.0.32` (required by Starlette for multipart file-upload parsing)
  to `backend/requirements.txt`.
- `backend/README.md` — documented `POST /extract` (curl example, validation order,
  full response shape example, and the synchronous-processing-time limitation).

**Storage approach:** The uploaded file is held only in memory for the duration of the
request (`io.BytesIO`, never written to disk) and discarded once the response is
returned — nothing is persisted. This satisfies "do not permanently store uploaded
documents yet" more strongly than a temp-file approach would (no filesystem path ever
exists for uploaded content, so there is nothing to clean up and no path-exposure
surface). This does not contradict `DEC-004` (no persistent database) — `DEC-004`
concerns the app's storage model for a document a user is actively viewing across
multiple requests (Phase 5/6 page-image serving), which does not exist yet. No new
`DECISIONS.md` entry was needed.

**Files added/modified:**
- `backend/app/models.py` (new)
- `backend/app/extraction.py` (new)
- `backend/app/main.py` (modified — added `POST /extract` and the chunked-read helper;
  `GET /health` untouched)
- `backend/tests/pdf_fixtures.py` (new)
- `backend/tests/test_extract.py` (new)
- `backend/requirements.txt` (modified — added `pdfplumber`, `python-multipart`)
- `backend/README.md` (modified — added API documentation section)

**Behaviour added/changed:** Backend now accepts a PDF upload and returns real
word-level extraction with bounding boxes, page dimensions, and provenance fields for
every word on every page. Errors are validated and reported cleanly at each stage
(wrong extension, non-PDF content, malformed PDF, oversized upload).

**Tests performed:**
- `pytest -v` in `backend/`: **13 passed, 0 failed** (11 new in `test_extract.py` + the
  2 pre-existing `test_health.py` tests, run together as the full suite). Covers: valid
  PDF → 200; top-level response structure; page metadata (`page_number`, `width`,
  `height`, `word_count`); region text and order matches source words; bounding boxes
  present and internally consistent (`x0 < x1`, `top < bottom`); `confidence` always
  `null`; blank-page PDF → 200 with empty `regions`; non-`.pdf` extension → 400;
  non-PDF content with a `.pdf` name → 400; malformed-but-`%PDF-`-prefixed content →
  422; error responses contain no traceback/internal-library names/filesystem paths;
  oversized upload (limit monkeypatched to 10 bytes for the test) → 413.
- Same non-blocking `StarletteDeprecationWarning` (httpx/httpx2) as Phase 2, unchanged.

**Manual verification (local server):**
- Started `uvicorn app.main:app` locally; confirmed `/health` still 200 before testing.
- `curl -F "file=@manual_test.pdf"` (generated from the same fixture builder) → `200`,
  correct JSON: 1 page, 200×200, 2 regions (`"Hello"`, `"World"`) with plausible,
  ordered bounding boxes.
- Non-PDF content uploaded as `.pdf` → `400 Uploaded file is not a valid PDF.`
- Malformed `%PDF-`-prefixed content → `422 The PDF could not be processed...`.
- Wrong extension (`.txt`) → `400 Only .pdf files are accepted.`
- Server stopped cleanly after testing; confirmed unreachable afterward.

**Manual RIL validation (read-only, `../poc-01/documents/native/RIL_IAR 2026.pdf`,
9.68 MB, never copied into this repo):**
- Uploaded via `curl` directly from its location in `../poc-01/`. `200 OK` in
  **75.6 seconds** for all 147 pages (word-level only — no text/table extraction, so
  faster than Experiment 1's combined 58 s figure is not directly comparable, but same
  order of magnitude for a document this size).
- Response: `filename: "RIL_IAR 2026.pdf"`, `page_count: 147`,
  `extraction_method: "pdfplumber_extract_words"`, `extraction_engine_version: "0.11.10"`
  (identical pdfplumber version to Experiment 1).
- Checked all seven representative pages (4, 5, 8, 22, 45, 60, 81): page dimensions are
  1190.55 × 841.89 pt on every page checked, matching Experiment 1's documented
  two-page-spread geometry. **Word counts matched Experiment 1's recorded values
  exactly on all seven pages** (4→1129, 5→1290, 8→858, 22→1394, 45→1140, 60→803,
  81→569 — cross-checked directly against
  `../poc-01/outputs/2026-08-17_pdfplumber_RIL_IAR_2026/inspection.json`), confirming
  this endpoint reproduces Experiment 1's extraction methodology exactly, not just
  approximately.
- Spot-checked region text/order on each page's first few words — reading order and
  bounding boxes look correct for in-column headings (e.g. page 4: "Chairman" → "and" →
  "Managing"). Page 45 shows a corrupted apostrophe glyph ("Board�s") — this is expected
  and consistent with Experiment 1's documented glyph-corruption finding; per
  requirement, this was **not** fixed or normalized — the raw word-level evidence is
  preserved faithfully.
- Did not verify multi-column reading-order scrambling, table fragmentation, or ₹
  corruption in detail beyond this — those are already-documented Experiment 1 findings
  this phase deliberately does not attempt to fix, and re-auditing them was out of scope
  for Phase 3's endpoint-correctness check.

**Deployment status:** NOT IMPLEMENTED. Local only, per Phase 3 scope.

**Known issues / limitations:**
- Extraction is fully synchronous; a ~150-page real document takes over a minute with
  no progress feedback. Acceptable for this phase; will need addressing (background
  processing or at least a "processing" UI state) once a frontend exists.
- No per-page partial-failure tolerance: if any single page throws during extraction,
  the entire request fails with `422` rather than returning partial results for the
  pages that succeeded. Not exercised by real data in this session's manual test since
  the RIL document extracted without error, matching Experiment 1's own "0 exceptions"
  finding.
- Same pre-existing `StarletteDeprecationWarning` as Phase 2 (httpx/httpx2), unchanged.
- `.env.example` still not added — still no environment variables exist in the running
  application (`MAX_UPLOAD_SIZE_BYTES` etc. are code constants, not env-configured, in
  this phase).

**Next immediate task:** Phase 4 (or equivalent) — begin the frontend, or extend the
backend with page-image rendering to support visual inspection (`FUNC-03`) — not started
in this session. Decision on which comes first is open.
