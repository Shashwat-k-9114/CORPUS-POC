# Corpus (prototype)

Corpus is a document-understanding and finding system. This repository is the first
independently deployable **prototype**: upload a native-text PDF, extract its content
with page and word-level provenance, and inspect the extraction alongside the original
page.

This is a small, fast-iterating prototype, not the final Corpus architecture. See
`PROJECT.md` for product scope and vision.

## Status

**Working end-to-end locally.** Upload a PDF in the browser, extract it, browse pages,
see word-level bounding boxes overlaid on the rendered page, click a word to inspect
its provenance. Not yet deployed. See `BUILD_LOG.md` for the current, authoritative
state of what has actually been built and verified.

## Project documents

- [`PROJECT.md`](./PROJECT.md) — what Corpus is, current scope, roadmap, status
- [`REQUIREMENTS.md`](./REQUIREMENTS.md) — itemized product/technical requirements
- [`DECISIONS.md`](./DECISIONS.md) — architecture/product decision record
- [`BUILD_LOG.md`](./BUILD_LOG.md) — session-by-session build history (source of truth
  for "what works right now")
- [`DEPLOYMENT.md`](./DEPLOYMENT.md) — deployment architecture, setup steps, and
  environment variables (Vercel + Render). **Deployment-readiness is prepared but no
  external deployment has occurred yet** — see that document's status tags.

## Planned architecture

- **Frontend:** Next.js + TypeScript (`frontend/`)
- **Backend:** Python + FastAPI (`backend/`)
- **Extraction:** pdfplumber, word-level bounding boxes only (v1)
- **Storage:** ephemeral, no database in v1

See `DECISIONS.md` for the reasoning behind each of these choices.

## Relationship to `../poc-01/`

`../poc-01/` contains earlier, completed research (pdfplumber, PaddleOCR, and an
in-progress Marker investigation) that informs this prototype's extraction choices. It
is **read-only** research evidence — never modified, moved, or duplicated by this
project. This repository reads from it (e.g., for test documents) but never writes to
it.

## Local development

Run the backend and frontend in two terminals.

**Backend** (see `backend/README.md` for full detail):

```
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Serves on `http://127.0.0.1:8000`. By default it accepts browser requests from
`http://localhost:3000` / `http://127.0.0.1:3000` (CORS) — copy `.env.example` to
`.env` and set `CORPUS_ALLOWED_ORIGINS` if your frontend runs on a different port (for
example, if port 3000 is already in use, Next.js will pick the next free port and you
must update this to match, or the browser will get CORS errors).

**Frontend** (see `frontend/` for its own scripts):

```
cd frontend
npm install
npm run dev
```

Serves on `http://localhost:3000` (or the next free port). Copy `.env.example` to
`.env.local` if the backend isn't at the default `http://127.0.0.1:8000`.

Then open the frontend URL, upload a native-text PDF, and explore. The RIL Integrated
Annual Report used throughout development (`../poc-01/documents/native/RIL_IAR
2026.pdf`) is a good test document — try the "Page 22" and "Page 81" quick-jump buttons
that appear for any document with enough pages.

## Deployment

Not yet deployed anywhere — no external hosting account or Git remote has been set up
for this project. Deployment-readiness (Render config for the backend, Vercel-ready
frontend, environment variable wiring, CORS configuration) is **prepared**; see
[`DEPLOYMENT.md`](./DEPLOYMENT.md) for the full architecture, setup steps, and an
explicit breakdown of what is locally validated vs. externally unvalidated. See
`DECISIONS.md` `DEC-009` for why Render (not a serverless/Function platform) was
chosen for the backend, and `BUILD_LOG.md` for the session this was prepared in.
