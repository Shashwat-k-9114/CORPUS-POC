# CORPUS — Architecture / Product Decision Record

Every meaningful technical or product decision made on this project is recorded here,
in order. Decisions are never silently changed — if a decision is superseded, the
original entry is kept and a new entry references it.

Statuses: `PROPOSED`, `ACCEPTED`, `SUPERSEDED`, `REJECTED`.

---

## DEC-001 — Frontend framework: Next.js + TypeScript

**Date:** 2026-08-18
**Status:** ACCEPTED

**Context:** The prototype needs a document viewer UI (page images + extracted text side
by side) that must be easy to deploy quickly and iterate on with a stakeholder.

**Options considered:**
- Plain React + Vite — lighter, but more manual routing/deployment wiring.
- Next.js + TypeScript — batteries-included routing, image handling, first-class Vercel
  deployment, strong ecosystem familiarity.
- Server-rendered Python templates (e.g., Jinja via FastAPI) — fewest moving parts, but
  weaker for an interactive viewer (page navigation, highlighting) and harder to iterate
  on visually.

**Decision:** Next.js + TypeScript, as proposed in the initial project brief.

**Why:** The viewer is inherently interactive (page navigation, future click-to-highlight
provenance), which favors a proper frontend framework over server-rendered templates.
Next.js has no strong reason to be rejected here, and deploys cleanly to Vercel with
minimal configuration, matching the "quick iteration, easy deployment" mandate.

**Consequences:** Two-language stack (TypeScript frontend, Python backend) instead of one
— accepted because the extraction work must stay in Python (pdfplumber, and any future
OCR/ML tooling from the research track).

---

## DEC-002 — Backend framework: FastAPI (Python)

**Date:** 2026-08-18
**Status:** ACCEPTED

**Context:** The backend's job is to accept a PDF upload, run extraction, and return
structured JSON. It must interoperate directly with pdfplumber and, later, whatever
research-track tools graduate into the product.

**Options considered:**
- Flask — minimal, familiar, but weaker built-in request/response validation.
- FastAPI — async-capable, automatic OpenAPI docs, Pydantic request/response validation
  out of the box.
- Django (+ DRF) — much more than this prototype needs (ORM, admin, auth scaffolding we
  explicitly don't want yet).

**Decision:** FastAPI.

**Why:** Pydantic models give us a clean, enforced way to define the Document / Page /
Region / Text data model described in the project brief and to keep the JSON contract
stable as the extraction engine changes underneath it. Auto-generated OpenAPI docs are a
low-cost win for a stakeholder-facing API that will be iterated on quickly. Django's
scaffolding (ORM, admin, auth) is explicitly out of scope for this prototype.

**Consequences:** Requires `uvicorn` (or equivalent ASGI server) for local dev and
deployment.

---

## DEC-003 — Extraction engine for v1: pdfplumber, default settings, word-level regions only

**Date:** 2026-08-18
**Status:** ACCEPTED

**Context:** `../poc-01/` Experiment 1 (`reports/experiment_01_summary.md`) already
evaluated pdfplumber's default-settings behavior on a real, complex native financial PDF
(RIL Integrated Annual Report). Findings: word-level extraction with bounding boxes is
positionally accurate and stable (0 exceptions across 147 pages) even when assembled
linear text (`extract_text()`) is scrambled by multi-column layouts; default table
detection (`find_tables()`) is unreliable in both directions (misses tables, shreds
others into dozens of fragments); currency symbols can be silently corrupted.

**Options considered:**
- pdfplumber, word-level extraction only — proven stable and positionally accurate per
  Experiment 1; explicitly excludes the two failure-prone surfaces (linear text reading
  order, table detection).
- pdfplumber, including `extract_text()` and `find_tables()` — matches "extraction" more
  completely, but Experiment 1 showed both are unreliable on realistic documents; using
  them here would mean the first product demo shows known-broken behavior.
- Marker or PaddleOCR — explicitly excluded from this prototype by the project brief;
  Marker research is still in progress in `../poc-01/` and not ready to graduate.

**Decision:** pdfplumber `extract_words()` (word-level regions with bounding boxes) as
the sole extraction surface for v1. `extract_text()` may be used only as a
non-authoritative convenience (if at all) — bounding-box word data is the source of
truth for what gets shown and traced. `find_tables()` is not used in v1.

**Why:** Experiment 1 is a direct, already-completed evaluation of exactly this choice.
Word-level bounding-box data was the one part of pdfplumber's default output shown to be
reliable; building the v1 provenance story on it (rather than on linear text or table
detection, both shown broken) directly follows the research rather than ignoring it.

**Consequences:** v1 will not display coherent paragraph-level reading order or table
structure — it will show words positioned on the page. This is a real product
limitation, not a bug, and must be visible to the stakeholder as such (see
`REQUIREMENTS.md`, non-requirements). Revisiting this is the most likely trigger for a
v2 extraction-engine decision.

---

## DEC-004 — No persistent database in v1; ephemeral in-memory/temp-directory storage

**Date:** 2026-08-18
**Status:** ACCEPTED

**Context:** The app needs to hold an uploaded PDF and its extraction results long enough
for a user to view/navigate it, but the project brief explicitly says not to add a
database "unless there is a demonstrated need," and v1 is single-document,
single-session focused.

**Options considered:**
- SQLite/Postgres-backed persistence — supports multi-document history across restarts,
  but no current requirement demonstrates the need, and it adds schema/migration surface
  to maintain.
- Ephemeral storage: uploaded PDF written to a temp directory keyed by a generated
  document ID, extraction results held in an in-memory registry for that process
  lifetime.

**Decision:** Ephemeral temp-directory + in-memory registry. No database in v1.

**Why:** Matches the "no database unless demonstrated need" instruction directly, and
keeps the backend stateless enough to redeploy trivially. A restart losing in-progress
documents is an acceptable, explicitly documented limitation for a single-stakeholder
prototype.

**Consequences:** Documents do not survive a backend restart or redeploy. This must be
stated plainly in the UI/docs, not hidden. If multi-document history or durability
becomes a real stakeholder need, this decision will need a superseding entry.

---

## DEC-005 — Region granularity for v1: word-level bounding boxes only

**Date:** 2026-08-18
**Status:** ACCEPTED

**Context:** The data model needs a concrete definition of "Region" between Page and
Text. Experiment 1 evidence supports word-level positional accuracy specifically, not
higher-level grouping (paragraphs, table cells, visual groupings like brace-grouped
names were shown to be lost by linear extraction).

**Options considered:**
- Word-level regions (one region per `extract_words()` word) — directly matches what
  Experiment 1 validated as reliable.
- Paragraph/line-level regions (grouping words by heuristic) — more readable, but
  introduces a grouping heuristic that hasn't been validated and risks re-introducing the
  reading-order problems Experiment 1 documented.
- Table-cell regions — rejected for v1 per `[[dec-003-extraction-engine]]`.

**Decision:** One Region per extracted word, each carrying its own bounding box, page
number, and order index from pdfplumber's word extraction order.

**Why:** Keeps the data model's provenance claims exactly as strong as the evidence
supports — no invented grouping, no invented reading order.

**Consequences:** The UI will need to present word-level regions in a way that's still
readable (e.g., rendered in extraction order per page) without pretending they form
verified paragraphs. Grouping is a legitimate future direction, not a v1 feature.

---

## DEC-006 — Single monorepo with `/backend` and `/frontend`, not two separate repos

**Date:** 2026-08-18
**Status:** ACCEPTED

**Context:** Repository structure needed to be fixed before Phase 1 work begins. The
directory already contained empty `backend/` and `frontend/` folders when this session
started.

**Options considered:**
- Two separate repositories (one per deployable) — cleaner deploy isolation, but doubles
  the git/PR/documentation overhead for a fast-iterating single-stakeholder prototype.
- One repository, two top-level app directories — simpler for a small team/solo
  iteration loop; still deploys each side independently (Vercel reads `frontend/`, the
  Python host reads `backend/`).

**Decision:** Single repository, `backend/` and `frontend/` as top-level directories, one
set of living docs (`PROJECT.md`, `REQUIREMENTS.md`, `DECISIONS.md`, `BUILD_LOG.md`) at
the root.

**Why:** Matches the existing (pre-created) scaffold, and minimizes process overhead for
a prototype meant to iterate quickly with one stakeholder. Both deploy targets
(Vercel/Python host) support deploying from a subdirectory of a monorepo.

**Consequences:** CI/deploy configuration (Phase 9) must be scoped to the correct
subdirectory per platform.

---

## DEC-007 — Test/reference PDF is read directly from `../poc-01/`, never copied into this repo

**Date:** 2026-08-18
**Status:** ACCEPTED

**Context:** `../poc-01/documents/native/RIL_IAR 2026.pdf` (9.23 MB) is the document used
for the representative test pages (4, 5, 8, 22, 45, 60, 81) called out in the project
brief's testing section, and is the same document Experiment 1 already evaluated.

**Options considered:**
- Copy the PDF into `corpus-poc` as a committed test fixture — makes the test suite
  self-contained, but commits a 9.23 MB binary and duplicates data that already exists,
  against the explicit instruction not to commit large PDFs unless required and not to
  touch/duplicate `../poc-01/` content unnecessarily.
- Reference `../poc-01/documents/native/RIL_IAR 2026.pdf` via a relative path from tests
  and manual verification steps, read-only, never copied or modified.

**Decision:** Reference the file in place via relative path. `.gitignore` blanket-excludes
`*.pdf` in this repo; automated tests that need a real document read from `../poc-01/`
directly and must skip gracefully (not fail the suite) if that path isn't present in a
given environment (e.g., a clean CI checkout that doesn't include the sibling directory).

**Why:** Directly follows the instruction to treat `../poc-01/` as frozen, read-only
research evidence and to avoid committing large PDFs. Keeps a single source of truth for
the test document instead of two copies that could drift.

**Consequences:** Any CI environment that checks out only `corpus-poc` (not its sibling
`poc-01`) will not have access to this fixture — tests depending on it must be written to
skip, not fail, in that case. A small synthetic PDF fixture may be added later, inside
`corpus-poc`, specifically for CI if this becomes a blocker (open question, not decided).

---

## Open questions (not yet decided)

- Deployment platform for the FastAPI backend (Render, Railway, Fly.io, or other) — 
  deferred to Phase 9; will be recorded as DEC-008 once evaluated against actual
  deployment constraints (page-image rendering is CPU/memory-bound, so free-tier limits
  matter).
- Whether a small synthetic PDF fixture should be committed to `corpus-poc` for
  CI-only testing (see `[[dec-007-test-fixture-source]]`).
