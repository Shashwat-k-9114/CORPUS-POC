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
