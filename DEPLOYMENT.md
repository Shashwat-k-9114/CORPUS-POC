# Corpus — Deployment Guide (Prototype)

**Status of this document: PREPARED. No external deployment has occurred.** Every
claim below is tagged `PREPARED`, `LOCALLY VALIDATED`, or `EXTERNALLY UNVALIDATED` —
read those tags literally. See `BUILD_LOG.md` for the session this was written in and
`DECISIONS.md` (`DEC-009`) for why this architecture was chosen.

---

## 1. Architecture

```
                    HTTPS                              HTTPS
   Browser  ─────────────────────►   Vercel   ─────────────────────►   (none — frontend
      │                            (Next.js,                            calls Render
      │                             static +                            directly from
      │                             client JS)                          the browser)
      │
      │  All API calls are made directly from the browser's JS to Render.
      │  Vercel serves only the static/client Next.js app; it is not a proxy.
      ▼
   HTTPS, CORS-restricted to the Vercel origin
      │
      ▼
   Render Web Service (persistent Python process)
      - FastAPI app (uvicorn)
      - in-memory document registry (30-min TTL, DEC-008)
      - local ephemeral disk: one temp dir per uploaded PDF
      - GET  /health
      - POST /extract
      - GET  /documents/{id}/pages/{n}/image
      - NO database, NO permanent storage, NO auth
```

- **Frontend:** Vercel (Next.js 16, static + client-rendered).
- **Backend:** Render, **Web Service** (a persistent container process) — explicitly
  **not** a serverless/Function product. See §2 for why.
- No other infrastructure. No database. No queue. No object storage. No auth provider.

## 2. Why the backend is not a Vercel/serverless function

See `DECISIONS.md` `DEC-009` for the full record. Short version: the backend performs
synchronous, CPU-bound PDF extraction that can run well over a minute for a large
document (measured: ~76–90s for the 147-page RIL report in Phases 3–5), and it keeps
state — an in-memory document registry plus a temp file per document — that must
survive from the `POST /extract` request to later `GET .../image` requests, for up to
30 minutes. Typical serverless/Function platforms (including Vercel Functions)
constrain request duration far below that on free/low tiers and do not guarantee a
warm, single, stateful process across separate invocations. A conventional
always-running web service process is the correct fit for *this specific backend* as
built — not a claim about Corpus's eventual production architecture.

## 3. Required accounts

All `EXTERNALLY UNVALIDATED` — no accounts have been created or logged into during
this preparation work.

- A Vercel account, connected to whatever Git host will hold this repository (a GitHub
  remote does not exist yet for this project — see §9).
- A Render account, same caveat.

## 4. Required environment variables

| Variable | Used by | Where set | Example |
|---|---|---|---|
| `CORPUS_ALLOWED_ORIGINS` | backend (CORS allow-list) | Render dashboard → Environment | `https://corpus-frontend.vercel.app` |
| `NEXT_PUBLIC_API_BASE_URL` | frontend (API client) | Vercel dashboard → Environment Variables | `https://corpus-backend.onrender.com` |

Local-dev defaults (already in place, unchanged by this phase):
`backend/.env.example` (`CORPUS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000`),
`frontend/.env.example` (`NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000`).
Production placeholders: `backend/.env.production.example`,
`frontend/.env.production.example` — both contain only placeholder URLs
(`REPLACE-WITH-DEPLOYED-...`), no real values, no secrets.

No other environment variables exist in the application. There are no API keys,
database URLs, or credentials of any kind in this prototype.

## 5. Local development

Unchanged from Phase 5 — see root `README.md`, `backend/README.md`,
`frontend/README.md`. Summary:

```
# backend
cd backend && python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# frontend
cd frontend && npm install && npm run dev
```

**LOCALLY VALIDATED** (Phases 2–5): both run and communicate correctly on
`localhost`.

## 6. Render setup steps (backend) — PREPARED, not yet executed

1. Push this repository to a Git host Render can read (GitHub/GitLab/Bitbucket). **Not
   done yet** — no remote is configured (see §9).
2. In the Render dashboard: New → Blueprint, point it at the repo, and Render should
   read `backend/render.yaml`. Alternatively, create the Web Service manually with:
   - Root directory: `backend`
   - Build command: `pip install -r requirements.txt`
   - Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - Health check path: `/health`
   - Runtime: Python (version pinned by `backend/runtime.txt`, `python-3.12.7` — chosen
     as a version these exact pinned dependency versions are known to support; **not**
     verified against Render's currently offered runtime list, see §11)
3. Set `CORPUS_ALLOWED_ORIGINS` in the Render dashboard once the Vercel URL is known
   (chicken-and-egg with step in §7 — deploy the backend first with a placeholder or
   with the frontend's *expected* Vercel URL, then correct it if the actual assigned
   URL differs).
4. Deploy. Confirm `GET https://<render-url>/health` returns `200` before touching the
   frontend.

`backend/render.yaml` schema is `PREPARED` against Render's documented Blueprint
format from training knowledge — **EXTERNALLY UNVALIDATED**, no live Render docs
lookup or actual Render account was available this session. Before first deploy,
confirm in Render's current docs: the `runtime: python` field name (older Render docs
used `env: python` — Render may still require one or the other), and that `rootDir`
and `healthCheckPath` are still valid top-level service fields.

## 7. Vercel setup steps (frontend) — PREPARED, not yet executed

1. Push this repository to a Git host (§9).
2. In Vercel: New Project → import the repo → set **Root Directory** to `frontend`.
   Framework preset should auto-detect Next.js.
3. Set `NEXT_PUBLIC_API_BASE_URL` in Vercel's Environment Variables (Production, and
   Preview if you want preview deployments to also work) to the Render backend URL
   from §6.
4. Deploy.

**EXTERNALLY UNVALIDATED** — Vercel's exact current UI/CLI flow was not exercised.

## 8. Connecting frontend to backend

1. Deploy backend first (§6), note its URL.
2. Set `NEXT_PUBLIC_API_BASE_URL` on Vercel to that URL, deploy/redeploy frontend.
3. Note the resulting Vercel URL, set `CORPUS_ALLOWED_ORIGINS` on Render to that exact
   URL (scheme + host, no trailing slash), and redeploy/restart the Render service so
   the new env var takes effect.

## 9. CORS configuration

The backend's CORS allow-list (`CORPUS_ALLOWED_ORIGINS`) must be set to the **exact**
deployed Vercel origin(s), comma-separated, e.g.:

```
CORPUS_ALLOWED_ORIGINS=https://corpus-frontend.vercel.app
```

If Vercel preview deployments (per-branch/PR URLs) need to reach the API too, add each
one explicitly. **Do not** set this to `*` — the app code does not support a wildcard
combined with credentials, and more importantly this API accepts uploaded documents;
an unrestricted allow-list is not appropriate even for a prototype. This is
unchanged from the constraint already documented in `backend/README.md` and
`DECISIONS.md` `DEC-008`.

## 10. Health check

`GET /health` → `{"status": "ok", "service": "corpus-backend", "version": "0.1.0"}`.
**LOCALLY VALIDATED** repeatedly since Phase 2. Use this as the Render health-check
path (already set in `render.yaml`) and as the first manual check after any deploy,
before testing anything else.

## 11. Deployment smoke-test procedure — to run once actually deployed

All steps below are **EXTERNALLY UNVALIDATED** until performed against real URLs.

1. `curl https://<render-url>/health` → expect `200` and the JSON above.
2. Open `https://<vercel-url>` in a browser with DevTools open (Network + Console
   tabs).
3. Upload a small PDF (a single page is enough) → confirm the request to
   `POST /extract` succeeds with no CORS error in the console, and the UI shows the
   document summary.
4. Select a page → confirm `GET .../pages/1/image` returns `200` with `image/png` and
   the coordinate headers (`X-Page-Width-Points` etc.) are visible in the Network
   panel's response headers (confirms `expose_headers` is working from a real
   cross-origin request, not just locally).
5. Confirm the bounding-box overlay is visible and click a word → confirm the
   Provenance panel populates correctly.
6. If Render's plan/timeout allows it (see §12): upload the RIL annual report
   (`../poc-01/documents/native/RIL_IAR 2026.pdf`, read-only, do not modify), and
   specifically test the "Page 22" and "Page 81" quick-jump buttons, repeating steps
   4–5 on each. This is the same scenario already fully verified locally in Phase 5 —
   the point of testing it again here is solely to confirm the *deployed* environment
   behaves the same way, not to re-derive new extraction results.

## 12. Known limitations to expect on a free/low-cost tier

None of the following have been observed on a real deployment — they are documented
risks based on the backend's known behavior (Phases 3–5) and typical free-tier
platform constraints, so they can be checked deliberately during the smoke test
rather than discovered by surprise:

- **Request timeout:** the 147-page RIL document took ~76–90s to extract locally.
  Some platforms/proxies impose a request timeout (commonly 30s–100s on free tiers)
  that could cut this off before the response completes. If this happens, it will
  need to be addressed by increasing the platform's timeout setting (if available on
  the plan) — not by changing the extraction to be asynchronous, which would be a
  real architecture change outside this phase's scope.
- **Cold starts / idle spin-down:** free-tier Render services typically spin down
  after a period of inactivity and take tens of seconds to wake on the next request.
  The very first request after idle may time out or feel slow; retry.
- **In-memory registry and temp files do not survive a restart.** A spin-down-and-wake
  cycle, or any redeploy, clears the document registry exactly like a local
  `Stop-Process` — this is consistent with `DEC-004`/`DEC-008`'s existing ephemeral
  design, not a new limitation, but it is more *frequent* on a free tier that
  auto-sleeps than it is in local development.
- **Upload size:** the app enforces its own 20 MB cap (`MAX_UPLOAD_SIZE_BYTES` in
  `backend/app/main.py`) regardless of platform; the RIL PDF (~9.68 MB) is within it.
  Some platforms/proxies impose their own separate request body limit — unverified
  against Render specifically.
- **CPU/memory:** page rendering at 150 DPI and word-level extraction across ~150
  pages is measurably CPU-bound (Phase 3–4 timings). A free-tier instance with a
  fraction of a shared CPU may be slower than local development, potentially pushing
  the 147-page RIL extraction closer to or past a request timeout.

## 13. Rollback / basic troubleshooting

- **Frontend shows a network error / CORS error in console:** check
  `NEXT_PUBLIC_API_BASE_URL` on Vercel matches the actual Render URL exactly (scheme,
  host, no typos), and `CORPUS_ALLOWED_ORIGINS` on Render matches the actual Vercel
  URL exactly. A mismatch on either side is the most likely cause — this is not a code
  bug, it is a configuration bug, and both apps already log/report this clearly (the
  Render CORS middleware silently drops disallowed origins by design; there is no
  server-side error to see, only a browser-side console error).
- **`GET /health` fails or times out:** check the Render service's own logs/dashboard
  for a crash or a cold-start-in-progress state before assuming the code is broken —
  this endpoint has been stable since Phase 2 locally.
- **Extraction request times out on a large document:** see §12 — this is a platform
  timeout/tier limitation, not a code defect, given the same document already
  succeeds locally (Phase 5).
- **To roll back:** redeploy the previous known-good commit on both Vercel and Render
  (both platforms keep deployment history natively). No database migrations or data
  exist to roll back — the app has no persistent state by design (`DEC-004`).

## 14. Summary: what is and isn't verified

| Area | Status |
|---|---|
| Backend runs locally, all endpoints work | LOCALLY VALIDATED (Phases 2–5) |
| Frontend runs locally, full workflow works | LOCALLY VALIDATED (Phase 5) |
| `backend/render.yaml` schema correctness | PREPARED — EXTERNALLY UNVALIDATED |
| Render Python runtime supports `python-3.12.7` and this project's pins | PREPARED — EXTERNALLY UNVALIDATED |
| Render request timeout accommodates a 147-page RIL extraction | UNKNOWN — EXTERNALLY UNVALIDATED |
| Render free-tier temp disk/in-memory behavior across a real request lifecycle | UNKNOWN — EXTERNALLY UNVALIDATED |
| Vercel deploys this Next.js app without further configuration | PREPARED — EXTERNALLY UNVALIDATED |
| CORS works correctly across two real deployed origins | UNKNOWN — EXTERNALLY UNVALIDATED |
| Actual deployed URLs | DO NOT EXIST YET |
