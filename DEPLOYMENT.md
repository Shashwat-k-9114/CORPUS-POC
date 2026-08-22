# CORPUS deployment runbook

## Local production topology

`docker compose up -d --build` starts PostgreSQL, migrations, MinIO, the idempotent
private-bucket initializer, FastAPI, the independent worker, and the production
Next.js frontend. The API and worker share only PostgreSQL and the configured
BlobStore contract; local Compose stores canonical and derived bytes in the persistent
`minio_data` volume through MinIO's S3 API. The frontend is at `http://127.0.0.1:3000`.

```powershell
docker compose up -d --build
docker compose run --rm migrate
.\scripts\validate-deployment.ps1
docker compose ps
```

MinIO is the local S3-compatible server. Its API is exposed at
`http://127.0.0.1:9000`, its console at `http://127.0.0.1:9001`, and Compose creates
the private `corpus-private` bucket using local-only `minioadmin` credentials. The
initializer is safe to run repeatedly; it never makes the bucket public. Staging is
ephemeral container disk, while final canonical and derived objects are promoted to
MinIO before database admission or representation linkage.

## Review deployment topology

The zero-cost review compromise is:

```text
Vercel Hobby (Next.js) → Render Free Web Service (FastAPI + worker processes)
                                      ↓
                           Supabase Postgres + private S3 bucket
```

Render local disk is never durable. The production BlobStore is `S3BlobStore` against
Supabase Storage's S3-compatible endpoint. A production system should split API and
worker into separate services; this POC keeps them as independently supervised OS
processes in one Render container because of the free-tier constraint.

### Client and custodian isolation

One running CORPUS deployment represents exactly one client. Client isolation is
physical: provision a separate PostgreSQL database, private S3-compatible bucket,
storage credentials, and deployment configuration for every client. `CORPUS_CLIENT_ID`
labels that deployment; it is not a runtime tenant switch and is not persisted in the
CORPUS schema. Custodians and corpora remain logical organizational boundaries inside
the selected client's database and bucket. The UI custodian selector therefore never
selects a client. Custodian-scoped keys and query boundaries provide defense in depth
inside the client deployment.

## Supabase setup

1. Create one Supabase project for this client only. Do not reuse a database across
   client deployments.
2. Apply `backend/migrations/001_initial.sql`, `002_admission_idempotency.sql`, and
   `003_durable_processing.sql` using the SQL editor or `python -m app.db.migrate`.
3. Use the Supavisor session/transaction-compatible PostgreSQL URL with
   `sslmode=require`; do not use a local filesystem path.
4. Create a private Storage bucket named `corpus-private` (or another client-specific
   name) in this client's project. Do not reuse a bucket across client deployments.
5. Create server-only S3 credentials and record the project S3 endpoint, region,
   access key, secret key, and bucket name.

Set the deployment identity as a non-secret provider variable, and set the following
credentials/configuration in Render's secret environment store, using
`backend/.env.production.example` as the inventory:

Non-secret: `CORPUS_CLIENT_ID` (the demonstration deployment uses `demo-client`).

Secrets: `CORPUS_DATABASE_URL`, `CORPUS_S3_ENDPOINT_URL`, `CORPUS_S3_REGION`,
`CORPUS_S3_BUCKET`, `CORPUS_S3_ACCESS_KEY`, `CORPUS_S3_SECRET_KEY`,
`CORPUS_REVIEW_TOKEN`, and `CORPUS_ALLOWED_ORIGINS`.

Validate the service without revealing secrets:

```powershell
docker compose exec api python -m app.diagnostics
```

The same command is the Render shell diagnostic. It reports only database/storage
status and the selected backend.

## Render setup

Use the repository-root `render.yaml` as the sole Blueprint. Render discovers that
path by default. Set `CORPUS_*` secret values in the Render dashboard, then deploy
the Docker web service.
Render supplies `PORT`.

- Build: Render Docker build from `backend/Dockerfile`.
- `CORPUS_CLIENT_ID`: the non-secret identifier for this one client deployment.
- The service must point to this client's database and private bucket credentials only.
- Start: `./entrypoint.sh`.
- Health: `/health`.
- Readiness: `/ready`.
- Migrations run before the API and worker are started.
- A worker exit terminates the container so Render restarts the pair.

Render Free may sleep after roughly 15 minutes of inactivity. The first browser request can be a cold start;
the worker pauses while asleep, but PostgreSQL jobs, leases, canonical objects, and
derived artifacts remain durable. Expired leases recover when the service wakes. No
self-pinging is used.

## Vercel setup

Create a Vercel Hobby project with root directory `frontend`. Set:

- `NEXT_PUBLIC_API_BASE_URL=https://<render-service>.onrender.com`
- `NEXT_PUBLIC_REVIEW_TOKEN_REQUIRED=true`

The reviewer token is never a `NEXT_PUBLIC_*` variable. Deploy with the standard
Vercel build (`npm ci`, `npm run build`) and verify the production URL before sharing.

### Provisioning a second client

Create a new Supabase project/database, a new private S3 bucket, new server-only
storage credentials, a new Render service configured with a new `CORPUS_CLIENT_ID`,
and a new Vercel frontend deployment pointing to that Render service. Do not point the
second client at the first client's database, bucket, or credentials. No application
runtime switch is involved.

## Verification and rollback

Run local gates before provider deployment:

```powershell
docker compose run --rm migrate
docker compose run --rm api sh -c "PYTHONPATH=/app python -m pytest -q"
cd frontend
npm test -- --run
npm run lint
npx tsc --noEmit
npm run build
npm run test:e2e
```

For rollback, redeploy the last known-good Render image and Vercel deployment. Do not
roll back migrations destructively; migrations are forward-only and canonical objects
are immutable. Teardown is provider-console scoped: remove the Vercel project, Render
service, and Supabase project only after exporting any review evidence.

## Demo data

The only destructive local reset is explicitly scoped to the `demo` custodian:

```powershell
.\scripts\demo.ps1 -Action reset -ConfirmReset
.\scripts\demo.ps1 -Action seed
```

The fixtures are synthetic/public review PDFs only. No personal or confidential source
material is part of the deployment workflow.
