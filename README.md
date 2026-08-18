# Corpus (prototype)

Corpus is a document-understanding and finding system. This repository is the first
independently deployable **prototype**: upload a native-text PDF, extract its content
with page and word-level provenance, and inspect the extraction alongside the original
page.

This is a small, fast-iterating prototype, not the final Corpus architecture. See
`PROJECT.md` for product scope and vision.

## Status

**Foundation phase — no application code yet.** See `BUILD_LOG.md` for the current,
authoritative state of what has actually been built. Do not assume anything below is
running until `BUILD_LOG.md` says so.

## Project documents

- [`PROJECT.md`](./PROJECT.md) — what Corpus is, current scope, roadmap, status
- [`REQUIREMENTS.md`](./REQUIREMENTS.md) — itemized product/technical requirements
- [`DECISIONS.md`](./DECISIONS.md) — architecture/product decision record
- [`BUILD_LOG.md`](./BUILD_LOG.md) — session-by-session build history (source of truth
  for "what works right now")

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

Not yet available — backend and frontend have not been implemented. This section will be
filled in as Phase 2/3 complete (see `BUILD_LOG.md`).

## Deployment

Not yet available. Deployment approach and constraints will be documented here once
Phase 9 completes (see `DECISIONS.md` open questions and `BUILD_LOG.md`).
