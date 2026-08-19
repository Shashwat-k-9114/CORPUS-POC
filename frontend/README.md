# Corpus frontend

Next.js + TypeScript app. See root `../PROJECT.md`, `../DECISIONS.md`,
`../REQUIREMENTS.md` for product/architecture context, and `../BUILD_LOG.md` for
current implementation status. For deploying this frontend (Vercel), see
`../DEPLOYMENT.md` and `.env.production.example` in this directory — prepared but not
yet externally validated (no deployment has occurred).

## Setup

```
npm install
```

Copy `.env.example` to `.env.local` if the backend isn't running at the default
`http://127.0.0.1:8000`.

## Run (development)

```
npm run dev
```

Serves on `http://localhost:3000` (Next.js picks the next free port if that one is
taken — check the terminal output). Requires the backend to be running and to allow
this origin via `CORPUS_ALLOWED_ORIGINS` (see `../backend/README.md`).

## Test

```
npm test    # vitest run
npm run lint
npm run build
```

## What's here

- `app/page.tsx` — the entire user-facing workflow (upload → extract → view → inspect),
  a single client component tree; no routing between app "pages" since there's only
  one screen with internal state (document/page/selected-region).
- `lib/api.ts` — the only code that talks to the backend. `lib/types.ts` mirrors
  `backend/app/models.py` by hand (no schema-generation step in this prototype).
- `lib/coords.ts` — the `pixel = point * (dpi / 72)` mapping from
  `../backend/app/rendering.py`, as a small pure, independently tested function.
- `components/` — `UploadPanel`, `DocumentSummary`, `PageViewer` (image + SVG bbox
  overlay), `ProvenancePanel`.

## Known limitations

- No routing/URL state — refreshing the page loses the current document (matches the
  backend's own ephemeral, no-database storage model; nothing to restore from anyway).
- Not deployed yet.
