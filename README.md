# CORPUS v0.1.0 POC

CORPUS is a durable document-admission and asynchronous page-processing proof of
concept. Uploads are streamed into custodian-scoped canonical storage; PostgreSQL
holds source identity, provenance, enrollment, jobs, checkpoints, and derived
lineage. Canonical bytes are never replaced by derived output.

## Local production-shaped stack

The Compose stack contains PostgreSQL, MinIO, migration and bucket-initializer
one-shots, API, worker, and the standalone Next.js frontend:

```powershell
docker compose up -d --build
docker compose ps
```

Open <http://localhost:3000>. API health and readiness are available at
<http://localhost:8000/health> and <http://localhost:8000/ready>. Local Compose uses
the application `BlobStore` abstraction backed by a private, persistent MinIO bucket
(`corpus-private`) for canonical and derived bytes. PostgreSQL stores metadata, hashes,
storage keys, and lineage; it does not store document bytes. The worker is separate so
it can be stopped and restarted without losing queued jobs, checkpoints, or MinIO
objects. MinIO's S3 API is at `http://localhost:9000` and its development console is
at `http://localhost:9001` (local-only credentials are defined in Compose).

## Verification

```powershell
docker compose run --rm migrate
docker compose exec -T api python -m pytest -q
docker compose exec -T api sh -c "pip install --no-cache-dir ruff mypy && ruff check app tests && mypy app"
cd frontend
npm test -- --run
npm run lint
npx tsc --noEmit
npm run build
$env:CORPUS_UI_URL = "http://127.0.0.1:3000"
npm run test:e2e
```

The acceptance suites in `backend/tests/*acceptance.py` exercise the running API
against real PostgreSQL. `scripts/validate-deployment.ps1` checks health/readiness.

## Hosted topology

The supported free-tier shape is Vercel (frontend) → Render (one Docker web service
running API and worker under supervision) → Supabase (PostgreSQL plus a private
S3-compatible bucket). Set the S3 credentials and database URL only in provider
secret stores. `backend/.env.production.example`, `DEPLOYMENT.md`, and
`SECRET_INVENTORY.md` list the required variables. `python -m app.diagnostics`
validates database and blob-store connectivity without printing secrets.

Hosted access is gated by `CORPUS_REVIEW_TOKEN`. The frontend asks for it once per
browser session and sends it in `X-Corpus-Review-Token`; it is never a public build
variable. Use the “Forget review token” control to clear session storage.

## Scope and limitations

The legacy `/extract` endpoint and bounding-box viewer remain available for derived
output inspection and compatibility. New durable UI flows do not call `/extract`.
OCR expansion, embeddings, vector databases, RAG, LLM findings, distributed queues,
and retrieval/search are intentionally out of scope. Render's local filesystem is
ephemeral, so hosted deployments must use Supabase/AWS S3-compatible storage.

See [DEPLOYMENT.md](DEPLOYMENT.md) for deployment and rollback procedures and
[REVIEWER_WALKTHROUGH.md](REVIEWER_WALKTHROUGH.md) for a five-minute review path.
