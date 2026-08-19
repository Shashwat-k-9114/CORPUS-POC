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

---

## 2026-08-18 — Phase 4: page-image rendering endpoint

**Task:** Make extraction output visually inspectable without a database or permanent
storage. `POST /extract` previously processed uploads entirely in memory and discarded
them; a page-image endpoint needs the PDF to still exist somewhere after that response,
so this phase adds bounded, ephemeral, ID-keyed temporary retention plus a page-image
endpoint. No frontend, no deployment.

**What was built:**
- `backend/app/storage.py` — in-memory `dict[str, DocumentRecord]` registry.
  `store_document(document_id, pdf_bytes, original_filename, page_count)` writes the PDF
  to a fresh `tempfile.mkdtemp(prefix="corpus_doc_")` directory as a fixed internal
  filename (`document.pdf` — never the client-supplied name). `get_document(document_id)`
  looks it up by dict key only — `document_id` is never concatenated into a filesystem
  path, so it cannot be used for path traversal regardless of its content.
  `DOCUMENT_TTL_SECONDS = 1800` (30 min); `_sweep_expired()` runs at the start of every
  `store_document`/`get_document` call and deletes (registry entry + temp directory) for
  anything past its TTL. `clear_all()` is a test/introspection helper also registered via
  `atexit` for normal-exit cleanup. See `DEC-008` for the full rationale and a real gap
  this session found (see Known issues below).
- `backend/app/rendering.py` — `render_page_png(pdf_path, page_number, resolution=150)`.
  Opens the stored PDF fresh with pdfplumber, calls `page.to_image(resolution=150)`
  (same call and same default resolution as `../poc-01/scripts/render_pages.py`), saves
  to PNG bytes, and returns `(png_bytes, image_width_px, image_height_px, page_width_pt,
  page_height_pt)`. No new dependency — `to_image()` is already available via
  `pdfplumber`'s existing `pypdfium2` dependency.
- `backend/app/models.py` — added `document_id: str` to `DocumentExtractionResponse`.
- `backend/app/extraction.py` — `extract_document()` now takes a `document_id`
  parameter and threads it into the response unchanged; the word-extraction call itself
  (`page.extract_words(use_text_flow=False, keep_blank_chars=False)`) was **not**
  touched.
- `backend/app/main.py`:
  - `POST /extract` now generates `document_id = uuid.uuid4().hex` before extraction,
    and — only on successful extraction — calls `storage.store_document(...)` so nothing
    is retained for a request that fails validation or extraction.
  - New `GET /documents/{document_id}/pages/{page_number}/image`: looks up the document
    (`404` if unknown/expired — the two are not distinguished in the response), validates
    `page_number >= 1` (`400`) and `page_number <= page_count` (`404`), renders via
    `render_page_png` (`422` on render failure, generic message), and returns the PNG
    with `X-Page-Number`, `X-Page-Width-Points`, `X-Page-Height-Points`,
    `X-Image-Width-Px`, `X-Image-Height-Px`, `X-Resolution-Dpi` headers so the
    point→pixel coordinate mapping is discoverable from the response itself, not just
    from documentation.
- `backend/tests/test_page_image.py` — 8 new tests (see below).
- `backend/tests/test_extract.py` — added a `document_id` presence/non-emptiness
  assertion to the existing structure test (the only change to an existing test; all
  other Phase 3 tests untouched and still pass).
- `backend/README.md` — documented the new endpoint, its validation order, response
  headers, and the coordinate-system relationship explicitly (point→pixel formula,
  no flip, uniform scale).
- `DECISIONS.md` — added `DEC-008` (ephemeral retention mechanism: lazy TTL sweep,
  no background scheduler, `atexit` for normal exit).

**No new dependency was added.** Rendering uses `pdfplumber`/`pypdfium2`, already
installed in Phase 3.

**Files added/modified:**
- `backend/app/storage.py` (new)
- `backend/app/rendering.py` (new)
- `backend/tests/test_page_image.py` (new)
- `backend/app/models.py` (modified — added `document_id`)
- `backend/app/extraction.py` (modified — `document_id` pass-through only)
- `backend/app/main.py` (modified — `/extract` now stores on success; added the image
  endpoint)
- `backend/tests/test_extract.py` (modified — one added assertion)
- `backend/README.md` (modified — new endpoint section)
- `DECISIONS.md` (modified — added `DEC-008`, renumbered the still-open deployment
  decision from `DEC-008` to `DEC-009` in the open-questions note)
- `REQUIREMENTS.md` (modified — see status changes below)

**Behaviour added/changed:** A successful `POST /extract` now returns a `document_id`
and causes the uploaded PDF to be retained server-side (temp directory) for up to 30
minutes. `GET /documents/{document_id}/pages/{page_number}/image` renders any page of a
currently-retained document as a PNG at 150 DPI.

**Tests performed:**
- `pytest -v` in `backend/`: **21 passed, 0 failed** (11 Phase 3 `test_extract.py` + 2
  `test_health.py` + 8 new `test_page_image.py`). New tests cover: successful extraction
  creates a retrievable `document_id`; valid page-image request → `200`; content type is
  `image/png` (also asserts PNG magic bytes on the body); unknown document ID → `404`;
  page number `0` → `400`; page number beyond the document's page count → `404`; response
  headers correctly describe the point→pixel mapping (asserted numerically against the
  known 200×200pt fixture page at 150 DPI, and that a square page renders to a square
  image); and document cleanup — after forcing `DOCUMENT_TTL_SECONDS` to `-1` via
  `monkeypatch`, `storage.get_document()` returns `None`, the temp directory no longer
  exists on disk, and the image endpoint returns `404` for that now-expired document.
  Same pre-existing httpx/httpx2 deprecation warning, unchanged.

**Manual verification (local server):**
- Started `uvicorn app.main:app`; confirmed `/health` still `200` first.
- Uploaded the real RIL PDF (see below) to obtain a real multi-page `document_id`.
- `GET /documents/{id}/pages/22/image` and `.../pages/81/image` (the two "structurally
  difficult" representative pages named in this phase's instructions) → both `200`,
  `image/png`, headers: `x-page-width-points: 1190.55`, `x-page-height-points: 841.89`,
  `x-image-width-px: 2481`, `x-image-height-px: 1754`, `x-resolution-dpi: 150` — matches
  the documented two-page-spread geometry from Experiment 1 exactly, and
  `2481/1754 ≈ 1190.55/841.89` (aspect ratio preserved).
- Error cases: unknown document ID → `404`; page `0` → `400`; page `9999` (document has
  147 pages) → `404 Page 9999 does not exist. This document has 147 pages.`.
- Downloaded both PNGs, opened with Pillow: correct pixel dimensions, non-blank
  (grayscale value range `0–255` on both, i.e. real content, not a blank/white canvas).
- **Coordinate-mapping check (page 22):** took the first word from `POST /extract`'s
  page-22 regions (`"Integrated"`, bbox `x0=51.0 x1=108.06 top=44.34 bottom=53.34` pt),
  applied the documented `pixel = point * (150/72)` formula, cropped the rendered image
  at the resulting pixel region (plus margin) — the crop visually shows the literal text
  "Integrated Approach to Sustainable..." exactly where the mapped bounding box placed
  it. This is a direct, positive visual confirmation that `POST /extract`'s coordinates
  and this endpoint's rendered image are in exact correspondence (requirement 8).
- Also visually reviewed a downsized full render of page 81 (printed pages 158–159):
  correctly shows the two side-by-side related-party-transaction tables — this is the
  exact page Experiment 1 flagged as its "worst table failure" case, confirming the
  rendering is legible and correctly oriented on a genuinely difficult layout, even
  though this phase does nothing to fix (and was not asked to fix) the underlying table
  extraction problem.
- Server stopped after testing.

**Manual RIL validation (read-only, `../poc-01/documents/native/RIL_IAR 2026.pdf`, never
copied into this repo):** covered above — pages 22 and 81 rendered correctly, at
2481×1754 px, with coordinate mapping verified both numerically and by visual crop.

**Deployment status:** NOT IMPLEMENTED. Local only, per Phase 4 scope.

**Known issues / limitations:**
- **`atexit`-based cleanup does not run on a forceful process kill.** Discovered
  directly in this session: stopping the manually-started dev server with `Stop-Process
  -Force` left a 9.23 MB orphaned `corpus_doc_*` temp directory (a full copy of the RIL
  PDF) on disk, which had to be removed by hand. A graceful stop (Ctrl+C/SIGINT) does
  trigger `atexit` correctly. Recorded as a real consequence in `DEC-008`; needs
  revisiting before real deployment (Phase 9).
- No per-request resolution parameter — rendering is fixed at 150 DPI. Not needed yet;
  would be a small, additive change if a future frontend wants e.g. a lower-res
  thumbnail.
- The image endpoint does not distinguish "document ID never existed" from "document ID
  expired" in its `404` response — deliberate (avoids leaking which IDs were ever
  valid), but means a stakeholder seeing a `404` after 30 minutes of inactivity won't
  get an explicit "your session expired" message. Acceptable for this phase; would want
  addressing once a frontend exists (`UX-01`-adjacent).
- No per-page partial-render fallback: if `render_page_png` fails for any reason, the
  whole request fails `422` — consistent with the same simplicity tradeoff already made
  for extraction failures in Phase 3.
- Same pre-existing `StarletteDeprecationWarning` (httpx/httpx2) as Phases 2–3,
  unchanged.

**Next immediate task:** Not started. Open choice for Phase 5: begin the frontend (now
that both extraction and page-image endpoints exist to build a viewer against), or
continue backend-only work. No decision made in this session.

---

## 2026-08-18 — Phase 5: first end-to-end browser demo (frontend)

**Task:** Build one complete, working vertical slice in the browser — upload → extract
→ select page → view page image → see word-level bounding boxes overlaid → click a
word → inspect its provenance — using only the existing Phase 2–4 backend, so the
prototype can actually be handed to a stakeholder. Not an extraction-system expansion.

**What was built:**
- Scaffolded `frontend/` with `create-next-app` (Next.js 16.3.1, React 19.2.8,
  TypeScript, App Router, ESLint flat config, Turbopack — per `DEC-001`, no new
  decision needed). Removed the generated boilerplate (`public/*.svg`, `favicon.ico`,
  `page.module.css` sample). Kept the tool-managed `AGENTS.md`/`CLAUDE.md` files
  (Next.js 16 writes these itself on `next dev` to point future coding agents at
  version-matched bundled docs — fighting them just recreates the diff, per their own
  header comment).
- Read the bundled Next.js 16 upgrade-guide docs (`node_modules/next/dist/docs/.../
  upgrading/version-16.md`) before writing app code, since this Next.js version is
  newer than training-data knowledge. Relevant conclusion: this app touches none of the
  breaking Async Request API changes (`params`/`searchParams`/`cookies`/`headers`) —
  it's a single static route with all interactivity client-side, calling the FastAPI
  backend directly via `fetch`/`XMLHttpRequest`, not Next.js server data-fetching.
- `frontend/lib/types.ts` — TypeScript interfaces mirroring `backend/app/models.py`
  exactly (`BoundingBox`, `Region`, `PageExtraction`, `DocumentExtractionResponse`).
- `frontend/lib/coords.ts` — `pointToPixel()`/`regionToPixelRect()`, the literal
  `pixel = point * (resolutionDpi / 72)` formula from the Phase 4 contract, as small
  pure functions. This is the "tiny test helper for coordinate mapping" the phase asked
  for, instead of a new debug API endpoint — no new backend surface was added for this.
- `frontend/lib/api.ts` — `extractDocument()` (XMLHttpRequest, not `fetch`, specifically
  to get real `upload`→`extracting` phase transitions from `xhr.upload` progress/load
  events — not simulated/fake progress) and `fetchPageImage()` (`fetch`, reads the
  `X-Page-Width-Points`/`X-Image-Width-Px`/`X-Resolution-Dpi` etc. response headers,
  converts the body to a blob URL). `ApiError` carries the backend's own `detail` text
  through unmodified — the UI never invents its own error copy.
- `frontend/components/UploadPanel.tsx` — the sole initial-screen action (`UX-03`):
  choose/drag a PDF, upload, with distinct uploading/extracting/error states.
- `frontend/components/DocumentSummary.tsx` — filename, page count, extraction method +
  pdfplumber version, `document_id`; page navigation (prev/next, numeric jump); two
  quick-jump buttons ("Page 22 (harder layout)", "Page 81 (harder tables)") that only
  render when the document actually has that many pages.
- `frontend/components/PageViewer.tsx` — fetches the page image, overlays an SVG with
  one `<rect>` per region (subtle default stroke, bolder on hover, solid highlight on
  selection), click sets the selected region. Uses `viewBox="0 0 imageWidthPx
  imageHeightPx"` from the response headers (not hardcoded assumptions) so the overlay
  and image scale together and stay aligned at any display size, aspect ratio preserved
  by construction.
- `frontend/components/ProvenancePanel.tsx` — shows text, `document_id`, `page_number`,
  `order_index`, `extraction_method`, all four bbox fields, and `confidence` — rendered
  as an explicit "not provided (pdfplumber's native-text extraction has no confidence
  score -- never fabricated)" message when `null`, never as a blank or a fake `0`.
- `frontend/app/page.tsx` — top-level orchestrator; plain `useState`, no state library
  (three variables: current document, current page, selected region — prop-drilled to
  four components; not enough state to justify Context/Redux).
- `frontend/app/layout.tsx`/`globals.css` — minimal light/dark-aware styling, system
  font stack (no `next/font/google` — avoids a build-time dependency on reaching
  Google's font CDN, which may not be reliable in every environment this gets built in).
- **Backend change (CORS — the one change this phase permitted):**
  `backend/app/main.py` now adds `CORSMiddleware`, origin allow-list from
  `CORPUS_ALLOWED_ORIGINS` (comma-separated env var, default
  `http://localhost:3000,http://127.0.0.1:3000`), and `expose_headers` for the six
  `X-*` coordinate headers — without `expose_headers`, `fetch()` in the browser cannot
  read custom response headers at all, which would have silently broken the coordinate
  mapping. `backend/.env.example` and `frontend/.env.example` added (first real env
  vars either app has needed — `CORPUS_ALLOWED_ORIGINS` and
  `NEXT_PUBLIC_API_BASE_URL`). No other backend behavior changed.
- Testing: added `vitest` + `@testing-library/react` + `jsdom` (pinned to versions
  actually compatible with this machine's Node 22.18 — `jsdom@28.1.0`, not the newest
  `30.0.1`, which requires Node ≥22.22 and produced an `EBADENGINE` warning; same kind
  of environment-driven pin as the backend's Phase 2 dependency fix). Config as
  `vitest.config.mts`/`vitest.setup.mts` (`.mts` to avoid an ESM/CJS loader warning
  without touching `package.json`'s module type, which could have affected Next's own
  tooling). `frontend/lib/coords.test.ts` (6 tests, the coordinate formula) and two
  component tests, `ProvenancePanel.test.tsx` (7) and `DocumentSummary.test.tsx` (3),
  focused specifically on the null-confidence contract and the page-22/81 quick-jump
  visibility rule. `backend/tests/test_cors.py` (3 tests) added for the new CORS
  behavior.
- Fixed one real `eslint` finding (`react-hooks/set-state-in-effect`) in
  `PageViewer.tsx`: the effect was synchronously calling `setState("loading")` at its
  own top, which React's linter flags as causing a wasted extra render. Fixed by
  remounting `PageViewer` via `key={`${documentId}-${pageNumber}`}` in `page.tsx` so a
  fresh mount's own `useState("loading")` default does the resetting, instead of an
  explicit synchronous reset inside the effect.

**Files added/modified:**
- `frontend/` — full Next.js app (see above); `package.json`, `tsconfig.json`,
  `next.config.ts`, `eslint.config.mjs` are `create-next-app` defaults, unmodified.
- `frontend/.env.example` (new)
- `backend/app/main.py` (modified — CORS middleware only)
- `backend/.env.example` (new)
- `backend/tests/test_cors.py` (new)

**Behaviour added/changed:** A user can now open the app in a browser, upload a PDF,
watch it get extracted, browse pages (including one-click jumps to pages 22/81), see
word-level bounding boxes drawn on the rendered page image, click any word to highlight
it and see its full provenance record, and see `confidence` explicitly marked as not
provided rather than blank or fabricated.

**Tests performed:**
- Backend: `pytest -v` → **24 passed, 0 failed** (the pre-existing 21 unchanged, plus 3
  new CORS tests). Same pre-existing httpx/httpx2 deprecation warning, unchanged.
- Frontend: `npm test` (`vitest run`) → **11 passed, 0 failed** — coordinate-formula
  correctness, confidence-null vs. real-value rendering, and quick-jump page-count
  gating. `npm run build` → compiles and type-checks cleanly. `npm run lint` → 0
  problems (after the fix above).
- Not covered by automated frontend tests (deliberately, to keep this phase's test
  surface proportionate): the full upload→extract XHR flow and the page-image `fetch`
  flow, which would need either a live backend or non-trivial `fetch`/`XMLHttpRequest`
  mocking. These were instead verified directly against the real running backend in
  the manual browser session below, which is a stronger check for this phase than a
  mocked unit test would have been.

**Manual RIL validation (read-only, `../poc-01/documents/native/RIL_IAR 2026.pdf`,
never copied into this repo) — full browser session, both servers running locally:**
- Note: port 3000 was already occupied by an unrelated local project in this
  environment; Next.js automatically moved the dev server to port 3002, and the
  backend was started with `CORPUS_ALLOWED_ORIGINS` including `:3002` for this session.
  Not a product issue — purely an artifact of this machine's environment; documented
  here because it's the kind of thing that would confuse the next person testing
  locally if unrecorded.
- Uploaded the real RIL PDF via the browser file input. UI correctly showed
  "Uploading…" then "Extracting… this can take over a minute for large documents."
  (real phase transitions from XHR progress events, not simulated), then rendered the
  document summary: `RIL_IAR 2026.pdf`, `147 pages`, `pdfplumber_extract_words
  (pdfplumber 0.11.10)`, a real `document_id`. Both "Page 22 (harder layout)" and "Page
  81 (harder tables)" quick-jump buttons were present (page count ≥ 81).
- Clicked "Page 22 (harder layout)" → correct 7-column-spread page rendered, matching
  Experiment 1's documented worst reading-order case. Zoomed in and clicked the word
  "Integrated" in the heading → it highlighted, and the Provenance panel showed
  `text: "Integrated"`, `page_number: 22`, `order_index: 0`,
  `extraction_method: pdfplumber_extract_words`, `bbox.x0: 51`, `bbox.x1: 108.06`,
  `bbox.top: 44.34`, `bbox.bottom: 53.34` — **bit-for-bit identical** to the values
  independently verified by direct pixel-crop in Phase 4's backend-only manual test,
  confirming the frontend's coordinate pipeline exactly matches the backend contract
  end-to-end, not just in isolation.
- Clicked "Page 81 (harder tables)" → correct related-party-transaction two-table
  spread rendered (same page visually confirmed in Phase 4). Provenance panel reset to
  its empty state on page change (confirmed correct behavior, not stale data). Clicked
  "Notes" (order_index 0) then "Financial" (order_index 1) in sequence — selection and
  provenance panel updated correctly each time, with only one region highlighted at a
  time.
- `confidence` displayed exactly as designed: italic, muted, explicit "not provided
  (pdfplumber's native-text extraction has no confidence score -- never fabricated)" —
  never blank, never a fake number.
- Verified the "invalid PDF" error state live: uploaded a `.txt` file renamed with
  `.txt` extension (real file, real network round trip) → UI showed
  `"Only .pdf files are accepted."` in a red error banner — the backend's own message,
  unmodified, confirming the frontend never invents its own error copy.
- Verified "New document" reset: returns cleanly to the upload screen with no leftover
  state.
- Checked the browser console: one hydration-mismatch warning caused by a third-party
  browser extension injecting a `data-writer-injected="true"` attribute onto `<body>`
  before React hydrated (same extension's icon is visible in every screenshot, on both
  this app and an unrelated site tested for comparison) — not an application defect,
  not fixed.
- Not directly exercised live in the browser this session: "expired document" and
  "unavailable page" error states. Both go through the exact same generic
  `ApiError`-message-rendering code path already demonstrated working for the
  "invalid PDF" case above (`UploadPanel`'s and `PageViewer`'s error branches are
  structurally identical), and the underlying backend responses for both cases were
  already directly tested in Phase 4's automated and manual verification. Reasoned as
  covered by code-path equivalence rather than re-demonstrated live; flagged here
  rather than silently assumed.
- Cleaned up after testing: stopped both dev servers; the backend was stopped with
  `Stop-Process -Force` (same known `DEC-008` gap as Phase 4 — `atexit` cleanup did not
  run), leaving two orphaned `corpus_doc_*` temp directories (9.23 MB each), removed by
  hand.

**Deployment status:** NOT IMPLEMENTED. Both apps run locally only, per this phase's
explicit instruction not to begin deployment.

**Known issues / limitations:**
- CORS origin allow-list defaults to port 3000; if the frontend dev server has to move
  to a different port (as it did in this very session), `CORPUS_ALLOWED_ORIGINS` must
  be set to match or the browser will get CORS errors. Not fixed generically — would
  require either a wildcard (rejected as a weaker default) or documenting the override,
  which is what was done (`backend/.env.example`, `backend/README.md`).
- No automated test exercises the real upload→extract or page-image `fetch` flow
  end-to-end (see Tests performed, above) — covered by manual browser testing instead
  for this phase.
- "Expired document" and "unavailable page" error UI were not directly re-triggered
  live in this session (see above) — same rendering code path as the demonstrated
  "invalid PDF" case, not independently re-verified live.
- Large pages (RIL: 800–1400 words) render that many SVG `<rect>` elements per page;
  performant in this manual test but not load-tested against a much larger document.
- Same `DEC-008` force-kill cleanup gap as Phase 4, reconfirmed in this session.
- No automated end-to-end (e.g. Playwright) test exists — this phase's browser
  verification was done manually, once, interactively.

**Documentation:** `BUILD_LOG.md` (this entry), `REQUIREMENTS.md` (statuses updated —
see diff), `README.md` (root — frontend section, full local-dev quick start covering
both servers), `backend/README.md` (CORS env var documented). `DECISIONS.md`
unchanged — CORS enablement was a mechanical necessity with no meaningful alternative
to record, not a new architectural decision.

**Next immediate task:** Not started. Deployment (Phase 9 in the original phase
numbering) is the explicitly named next small task, now that the local app is fully
working end-to-end.

---

## 2026-08-19 — Phase 6: deployment-readiness preparation (no deployment performed)

**Task:** Prepare the existing Phase 5 prototype so it can be deployed (Vercel +
Render) as soon as external account/repository access is available. No GitHub remote
or deployment CLI/account access existed in this environment — confirmed directly
(`git remote -v` empty; `gh`/`vercel`/`render`/`flyctl`/`railway` all "command not
found"). This session did **not** deploy, push, log into, or authenticate against any
external service.

**What was built:**
- `backend/render.yaml` — Render Blueprint for the backend as a persistent **Web
  Service** (not serverless): `rootDir: backend`, `buildCommand: pip install -r
  requirements.txt`, `startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT`,
  `healthCheckPath: /health`, `CORPUS_ALLOWED_ORIGINS` declared with `sync: false` (must
  be set manually in the Render dashboard once a real Vercel URL exists — never
  guessed or hardcoded). Schema written from documented Render Blueprint knowledge;
  **not** verified against a live Render account or current docs (no external lookup
  was performed) — explicitly flagged as such in the file's own header comment and in
  `DEPLOYMENT.md`.
- `backend/runtime.txt` (`python-3.12.7`) — pins a Python version these exact
  dependency pins are known to support; chosen because Render needs *some* version
  signal and none existed yet (not redundant with `render.yaml`, which declares no
  `PYTHON_VERSION`).
- `backend/.env.production.example`, `frontend/.env.production.example` — placeholder
  values only (`REPLACE-WITH-DEPLOYED-...`), no real URLs, no secrets.
- `DEPLOYMENT.md` — full deployment guide: architecture diagram, why the backend is
  not serverless, required accounts, required env vars, local dev recap, Render setup
  steps, Vercel setup steps, how to connect the two, CORS configuration, health check,
  a smoke-test procedure to run once real URLs exist, known tier limitations (request
  timeout, cold start, ephemeral disk/registry, upload size, CPU/memory), and
  rollback/troubleshooting notes. Every claim is tagged `PREPARED`, `LOCALLY
  VALIDATED`, or `EXTERNALLY UNVALIDATED` — a summary table closes the document.
- `DECISIONS.md` — added `DEC-009` (Render for the backend as a persistent web
  service, Vercel for the frontend; full reasoning against a serverless/Function
  backend given the measured ~76–90s RIL extraction time and the in-memory-registry +
  temp-disk state from `DEC-008`). Explicitly marked as a prototype deployment
  decision, not a final production architecture decision. Resolved the stale
  "will be recorded as DEC-009" placeholder in the old open-questions note.
- `REQUIREMENTS.md` — `DEPLOY-01`/`DEPLOY-02` moved from `PLANNED` to `READY` (platform
  chosen, configuration prepared, nothing externally validated yet — deliberately not
  `VALIDATED`, since no deployment exists); `DEPLOY-03` updated to note the new
  production `.env` examples; `DEPLOY-04` left `PLANNED` (cannot be validated without a
  real deployment).
- `README.md`, `backend/README.md`, `frontend/README.md` — pointers to
  `DEPLOYMENT.md` and the new `.env.production.example` files, each explicit that
  preparation is done but nothing is deployed.

**Files added:**
- `backend/render.yaml`
- `backend/runtime.txt`
- `backend/.env.production.example`
- `frontend/.env.production.example`
- `DEPLOYMENT.md`

**Files modified:**
- `DECISIONS.md`, `REQUIREMENTS.md`, `README.md`, `backend/README.md`,
  `frontend/README.md`

**Bug found and fixed during this session's own validation pass:**
`frontend/.gitignore` (a `create-next-app` default from Phase 5, not something written
by hand) contains a blanket `.env*` rule. That silently excluded `frontend/.env.example`
from every commit since Phase 5 — despite Phase 5's own report claiming it was
committed — and would have done the same to this phase's new
`frontend/.env.production.example`. Neither file contains a secret (placeholder/
localhost values only), but `DEPLOY-03` requires them to actually be tracked as
documentation. Fixed by adding `!.env.example` and `!.env.production.example`
negation lines to `frontend/.gitignore`; both files are tracked as of this commit.
Caught by this phase's own "verify no secrets/real URLs are committed" check
surfacing the opposite problem — a file that should have been committed wasn't.

**Behaviour added/changed:** None — no application code was touched. Extraction
methodology, CORS logic, storage/TTL behavior, and all endpoints are unchanged from
Phase 5.

**Tests performed:** See the validation results reported at the end of this session's
conversation (backend `pytest`, frontend `vitest`/`build`, and a structural review of
`render.yaml` and the production env-var wiring) — recorded there rather than
duplicated here to avoid drift between two copies of the same numbers; this entry is
the narrative record, the end-of-session report is the exact figures.

**Deployment status:** NOT IMPLEMENTED. Nothing has been deployed. `render.yaml` and
the Vercel setup steps are prepared but externally unvalidated.

**Known issues / limitations:** See `DEPLOYMENT.md` §12 and §14 for the full,
explicit list of what remains unverified (Render Blueprint schema correctness, Python
runtime availability, request-timeout headroom for a 147-page extraction, cold-start
behavior, CORS across two real origins) — not duplicated here.

**Next immediate task:** Obtain a Git remote and Render/Vercel account access (an
external action for the project owner, not something achievable from this
environment), then execute the steps in `DEPLOYMENT.md` §6–§7 and run the smoke test
in §11 against real URLs.

---

## 2026-08-19 — Python runtime verification (post-deployment finding, no code changed)

**Task:** After the Phase 6-prepared backend was actually deployed to Render
(`https://corpus-poc.onrender.com`, commit `d180d6645fecbd8842f2b440caf449a7dd8c5909`)
and a smoke test was run, confirm whether `backend/runtime.txt` (intended to pin
Python 3.12.7) was actually honored by the live deployment. This session made **no
code, configuration, or deployment changes** — verification only.

**Observed fact:** The Render build log for this deployment reads:
`==> Using Python version 3.14.3 (default)`, immediately followed by a link to
Render's own docs on specifying a Python version
(`https://render.com/docs/python-version`).

**Evidence:** Fetching that exact doc page shows Render resolves the Python version
via, in order: (1) a `PYTHON_VERSION` environment variable, (2) a `.python-version`
file at the repo root, (3) a default based on the service's creation date — and
explicitly states services created on/after 2026-02-11 default to **3.14.3**. Render's
docs do not mention `runtime.txt` (the Heroku-style filename this repo uses) as a
recognized mechanism at all. The deployed version (3.14.3) exactly matches Render's
documented default, not a value that could plausibly have come from a 3.12.7 pin.

**Interpretation:** `runtime.txt` was **not honored** by Render — confirmed with high
confidence (converging evidence: wrong filename/format for Render's documented
mechanism, the deployed version matching Render's documented default exactly, and the
build log's own "(default)" label), though not something provable from outside
Render's own resolver logic. The service ran Python 3.14.3 for this deployment, not
3.12.7.

**Impact assessed as low, but documentation/configuration accuracy is genuinely
affected:** This project's dependency pins (`fastapi==0.141.1`, `pydantic==2.13.4`,
etc., see Phase 2) were originally chosen specifically because they had to work on
Python 3.14 locally — so 3.14.3 on Render is not an unvalidated combination; if
anything it's closer to what was actually tested locally than 3.12.7 would have been.
The build completed cleanly with no dependency-resolution errors. The genuine problem
is that `backend/runtime.txt`, `DEPLOYMENT.md`, and this file's own Phase 6 entry
asserted 3.12.7 was what would be deployed, and that assertion was false — corrected
in `DEPLOYMENT.md` as of this entry.

**Explicitly kept separate — not part of this finding:** The RIL `/extract` 502
after ~55s (observed during the same smoke test) remains a **separate, unresolved
investigation**. Nothing about the Python-version finding above explains or resolves
it — a build-time version-resolution gap does not produce a mid-request timeout.
That investigation is still open and tracked independently.

**Files modified:** `DEPLOYMENT.md` (§6 Render setup steps, §14 verification summary
table) — corrected to state the actual deployed Python version and why the intended
pin didn't take effect. `backend/runtime.txt` **unchanged** (still asserts 3.12.7 —
left as-is pending an explicit decision on the actual fix, per instruction not to
modify it this session).

**Tests performed:** None — documentation-only change, no application code touched,
no re-validation required. The RIL upload was not retried.

**Next immediate task:** Two independent, still-open items, neither resolved by this
entry: (1) decide and apply the actual Python-version fix (likely a `.python-version`
file and/or a `PYTHON_VERSION` env var, with its placement relative to
`rootDir: backend` confirmed before relying on it) — not yet approved or made; (2)
continue the separate RIL `/extract` 502 investigation, which still needs the actual
Render runtime/request logs for the relevant timestamp window to proceed past the
current inference-only diagnosis.

---

## 2026-08-19 — Python runtime fix: dual `.python-version` (config only, not redeployed)

**Task:** Apply the approved fix for the Python-runtime finding above. User explicitly
approved a "dual-location" resolution to an ambiguity that further research could not
settle (see immediately below) rather than guessing a single location. Config-only —
no code, dependency, or Render-setting change; not deployed.

**The unresolved ambiguity, investigated before making any change:** Render's
Python-version doc states `.python-version` belongs "in the root of your repo."
Render's separate monorepo-support doc states "files outside your service's root
directory are not available to the service at build time or at runtime" once
`rootDir` is set (ours is `rootDir: backend`). These two statements don't clearly
resolve which "root" governs *version discovery specifically* — version detection
could plausibly happen at the true git-clone root before `rootDir` scoping applies to
the rest of the build, or it could already be scoped by `rootDir` like everything
else the second doc describes. A further search for community/support discussion of
this exact combination found nothing that settles it either. This was reported to the
user as a genuine ambiguity rather than guessed past, per instruction; the user then
explicitly approved covering both readings rather than resolving the ambiguity by
further guessing.

**What was changed:**
- Created `.python-version` (repo root) — content: `3.12.7`
- Created `backend/.python-version` — content: `3.12.7`
- Removed `backend/runtime.txt` (confirmed non-functional — see the prior entry)
- `backend/render.yaml` — **not modified**: it contains no reference to `runtime.txt`,
  so there was nothing outdated in it to correct.
- `DEPLOYMENT.md` — §6 (Render setup steps) and §14 (verification summary table)
  updated to describe the fix, explicitly labeled `PREPARED`/`EXTERNALLY
  UNVALIDATED` since it has not been tested against a real redeploy, and explicitly
  stating the dual placement is a hedge for an unresolved ambiguity, not a claim that
  Render requires or documents both locations.
- `DECISIONS.md` — not modified. This is a configuration correction with one
  reasonable, low-cost, easily-reversible resolution (duplicate a one-line file),
  not a decision with meaningfully competing architectural alternatives — doesn't
  meet the bar `DECISIONS.md` sets for its own entries.
- `README.md` / `backend/README.md` — checked, contain no Python-version deployment
  claims to correct (they don't mention `runtime.txt`, `.python-version`, or a
  specific Python version at all).

**Tests performed:** `pytest` — see result reported at the end of this session's
conversation. No frontend changes, no frontend tests run. The RIL upload was **not**
retried; the 502 investigation was **not** touched by this work.

**Deployment status:** UNCHANGED — still NOT redeployed since Phase 6. This fix exists
only in the local commit; it has not been pushed or verified against a real Render
build. Whether Render actually finds either (or neither, or both) `.python-version`
file remains genuinely unverified until a controlled redeploy happens.

**Next immediate task:** A controlled Render redeploy to observe the actual build log
and confirm which (if either) `.python-version` location Render used — this would
also retroactively resolve the ambiguity documented above for future reference. Still
separately open and untouched: the RIL `/extract` 502 investigation.

---

## 2026-08-19 — Deployment verification checkpoint: commit `2747d20` live, Python version unverifiable

**Task:** Push the local Python-version fix, let Render redeploy from it, and verify
the deployment. Config/verification only — no application code, dependency, or Render
setting changed.

**What happened:**
- `git push origin master` — clean fast-forward, `d180d66..2747d20`. `origin/master`
  now matches local `HEAD`.
- Render auto-deployed from the new commit.
- Attempted to obtain the new build log to check for the "Using Python version..."
  resolution line (the one piece of evidence that would settle which, if either,
  `.python-version` file Render honored). **Not available:** Render's runtime/deploy
  log view for this service does not expose that build-resolution line at all — only
  the runtime/deploy log, not the earlier build-phase output that contained it in the
  original deploy. Did not keep searching for it or attempt another redeploy to try
  to surface it, per instruction.
- Re-verified the live deployment directly instead, using only a small (1-page,
  2-word) test PDF — **not** the RIL document:
  - `GET /health` → `200 OK`
  - `POST /extract` (small PDF) → `200 OK`, new `document_id`
    (`f4ab272f142847f993b73fbc1367cff3`), correct page/region/bbox structure,
    `confidence: null` — matches local and prior-deploy behavior exactly
  - `GET /documents/{document_id}/pages/1/image` → `200 OK`, `image/png`

**Conclusion — stated exactly as instructed, no more and no less:**
- Commit `2747d20` is deployed and live; the service is reachable and the core
  request/response pipeline (health, extract, page-image) works correctly.
- The deployment starts successfully under Uvicorn; `WEB_CONCURRENCY=1` is Render's
  own setting for this service (seen in the original deploy's build log, and start
  command unchanged since — not re-observed fresh for this exact commit, since a
  fresh build-phase log was not obtainable this time; the three passing endpoint
  checks above are strong indirect corroboration the same startup succeeded again).
- **Which Python version Render actually selected for this deployment is
  unverified and is being treated as permanently unverifiable through the log
  access available for this project** — not "still pending," a real dead end for
  this specific evidence path. **3.12.7 is explicitly not being claimed as
  confirmed.** Neither `.python-version` location can be said to have been honored.
- The `.python-version` placement ambiguity (root vs. `backend/`, documented in the
  prior entry) remains unresolved — the evidence that would have settled it was not
  obtainable.

**Files modified:** `DEPLOYMENT.md` (§6 Render setup steps updated to reflect the
completed-but-inconclusive redeploy; §14 summary table updated — the Python-version
row now reads "permanently unverifiable via the available evidence," the URL row
corrected to the real live backend URL instead of the stale "do not exist yet"; new
§15 "Deployment verification record" added with the specific facts above).

**Tests performed:** No application code changed, so no local test suite re-run was
required for this checkpoint — the three checks above were live requests against the
deployed service, not local `pytest`/`vitest` runs.

**Deployment status:** Backend LIVE at `https://corpus-poc.onrender.com`, commit
`2747d20`. Frontend still NOT deployed.

**Explicitly untouched by this checkpoint:** The RIL `/extract` ~55s 502 — not
retried, not investigated further, remains a separate open item.

**Next immediate task:** Two independent, still-open items: (1) the RIL 502
investigation (needs Render request-level logs for that specific timestamp, still not
obtained); (2) whether to pursue the Python-version question further through some
channel other than this project's available Render log view (e.g. Render support
directly) is an open decision, not a task in progress — no next step has been
committed to on that front.
