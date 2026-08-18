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
