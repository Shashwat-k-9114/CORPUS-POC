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

## DEC-008 — Ephemeral document retention: generated ID, lazy TTL sweep, no background scheduler

**Date:** 2026-08-18
**Status:** ACCEPTED

**Context:** `DEC-004` established ephemeral temp-directory storage keyed by a generated
document ID instead of a database, but did not specify a concrete eviction mechanism.
Phase 4 needs an uploaded PDF to remain available on disk between the `POST /extract`
response and later `GET /documents/{id}/pages/{n}/image` requests, for a bounded time,
without a database, a background job scheduler, or permanent storage.

**Options considered:**
- A background thread/scheduler that periodically sweeps expired documents — bounds
  retention even with no further traffic, but adds a moving part (thread lifecycle,
  startup/shutdown wiring) disproportionate to a single-process prototype.
- Lazy sweep: check for and evict expired documents inline, at the start of every
  storage read/write call, before proceeding. No thread, no scheduler.
- Rely solely on the OS temp directory's own eventual housekeeping — too indefinite;
  does not satisfy "bounded lifetime."

**Decision:** Lazy sweep on every `store_document()`/`get_document()` call, TTL = 30
minutes, plus an `atexit` hook that clears all retained documents on normal process
exit. Document IDs are generated with `uuid.uuid4().hex` and used only as an in-memory
dict key — never concatenated into a filesystem path — so an unrecognized or malicious
document ID cannot reach the filesystem at all; the actual temp-file path is generated
independently via `tempfile.mkdtemp()` and never derived from client input.

**Why:** Satisfies "bounded lifetime or explicit cleanup mechanism" without a background
thread — the smallest mechanism that actually bounds retention. A single-stakeholder
prototype does not need cleanup to happen the instant a document expires; it only needs
to happen before storage grows unbounded, which a per-request sweep achieves.

**Consequences:** A document can sit on disk past its 30-minute TTL if no further
storage-layer request of any kind arrives to trigger a sweep — accepted, since
inactivity also means no one is viewing that document. More significantly: **the
`atexit` hook does not run on a forceful process kill.** This was confirmed directly
during this session's manual testing — stopping the dev server with `Stop-Process
-Force` left a 9.23 MB orphaned temp directory that had to be removed by hand. A
graceful shutdown (Ctrl+C/SIGINT, which `uvicorn` handles normally) does trigger it.
This is a known gap that would need an OS-level temp-directory reaper or a real
background sweep for a production deployment; acceptable for local development, where
restarts are typically graceful, but worth revisiting before Phase 9.

---

## DEC-009 — Prototype deployment: Render (backend web service) + Vercel (frontend)

**Date:** 2026-08-18
**Status:** ACCEPTED (deployment-readiness preparation only — no external deployment
has occurred as of this decision; see `DEPLOYMENT.md`)

**Context:** The Phase 5 application (FastAPI backend + Next.js frontend) works fully
end-to-end locally and needs to be reachable at a public URL so a stakeholder can test
it without local setup (`PROD-04`). The backend's actual runtime behavior constrains
which hosting model is viable: it performs synchronous, CPU-bound PDF word extraction
that measured ~76–90 seconds for the 147-page RIL report (Phases 3–5); it keeps an
in-memory document registry with a 30-minute TTL (`DEC-008`); and it writes each
uploaded PDF to local temp disk, which must still be present when a later
`GET /documents/{id}/pages/{n}/image` request arrives, possibly minutes afterward.

**Options considered:**
- **Vercel Functions (serverless) for the backend too**, matching the frontend's
  platform for simplicity — rejected. Serverless/Function products are built around
  short-lived, independently-invoked, typically stateless execution environments;
  common free/low-tier request-duration limits (seconds to tens of seconds) are not
  reliably long enough for the measured ~76–90s extraction time, and there is no
  guarantee that two requests (the initial `/extract` and a later `/pages/.../image`
  request) land on the same warm instance with the same local disk and the same
  in-memory Python process. Making this work would require redesigning the backend
  around async job processing and/or external state (a queue, a database, object
  storage) — explicitly out of scope for this phase and not something the current
  prototype needs to prove.
- **A conventional persistent web-service host for the backend** (Render, Railway,
  Fly.io, and similar all fit this description) — a single long-running container
  process, matching exactly how the backend already runs locally (`uvicorn` serving
  requests continuously, one process, one temp directory tree, one in-memory dict for
  the lifetime of the process).
- **Among persistent-process hosts, Render specifically** — chosen over Railway/Fly.io
  primarily because it has a straightforward, well-documented free tier for exactly
  this workload shape (a single Python web service) and a Blueprint (`render.yaml`)
  mechanism for reproducible, git-tracked configuration. This is not a claim that
  Railway or Fly.io would be unsuitable — either would likely work under the same
  reasoning above — Render was picked as *a* reasonable default, not because the
  others were evaluated and rejected on technical merit.

**Decision:** Frontend on Vercel (matches `DEC-001`'s existing framework choice
directly — Vercel is Next.js's own platform). Backend on Render, deployed as a **Web
Service** (persistent process), not a Function/serverless product, configured via
`backend/render.yaml`.

**Why:** The backend's actual behavior — long synchronous requests, an in-memory
registry, and temp-file state that must outlive a single request — needs a host that
keeps one process running continuously with a stable local filesystem, which is
precisely what a conventional web-service deployment provides and a serverless
Function deployment does not reliably provide. This lets the prototype deploy with
**zero changes to the application's architecture** (no new database, no queue, no
async job system) — the deployment target was chosen to fit the existing prototype,
not the other way around.

**This is a prototype deployment decision, not a final Corpus production-architecture
decision.** If Corpus's real usage later needs multi-instance scaling, durable
document storage across restarts, or genuinely long-running background processing,
that will warrant its own, separately-evaluated architecture decision — likely
superseding both this entry and `DEC-004`/`DEC-008`.

**Consequences:** Free-tier persistent-process hosts commonly idle-spin-down and cold-
start, which is a real, expected limitation on this plan (documented in
`DEPLOYMENT.md` §12) — this is a tier/cost tradeoff, not a defect introduced by this
decision. `backend/render.yaml`'s exact field names are written from documented
Blueprint schema knowledge and are **not** verified against Render's current live
docs or an actual Render account (no external lookup or account access was available
during this preparation work) — flagged explicitly in `DEPLOYMENT.md` rather than
presented as confirmed.

---

## DEC-010 — One client per deployment with physical database and bucket isolation

**Date:** 2026-08-22
**Status:** ACCEPTED

**Context:** The reviewer clarified that each client must receive a separate database
and separate storage bucket. The earlier custodian-scoped model provided logical
isolation inside one deployment but did not define the client boundary.

**Decision:** A running CORPUS deployment represents exactly one client. Provisioning a
client creates a new PostgreSQL database, private S3-compatible bucket, server-only
storage credentials, `CORPUS_CLIENT_ID`, and deployment configuration. The process uses
one database URL and one bucket for its entire lifetime. There is no runtime database
switching, shared multi-client table, dynamic credential resolution, or central control
plane. Custodians and corpora remain logical organizational boundaries inside that
client, and custodian-scoped keys remain defense in depth.

**Consequences:** `CORPUS_CLIENT_ID` is deployment configuration rather than persisted
schema, so no migration is required. The existing hosted environment is one
demonstration client. A second client is a separate provider deployment and does not
share the first client's database, bucket, or credentials.

---

## Open questions (not yet decided)

- Whether a small synthetic PDF fixture should be committed to `corpus-poc` for
  CI-only testing (see `[[dec-007-test-fixture-source]]`).
- Whether Render's actual free-tier request timeout and CPU allocation can complete a
  147-page RIL-scale extraction — genuinely unknown until a real deployment is tested
  (see `DEPLOYMENT.md` §12, §14).
