# CORPUS v0.1.0 deployment wizard

This wizard describes the repository’s actual hosted topology:

```text
Vercel Hobby (frontend) → Render Free Docker web service → Supabase Postgres + private S3 bucket
```

Each deployed instance is one client. Client isolation is physical infrastructure
isolation: one client gets one PostgreSQL database, one private S3-compatible bucket,
one set of storage credentials, one Render deployment, and one frontend deployment.
`CORPUS_CLIENT_ID` labels the deployment. Custodians and corpora are internal logical
boundaries inside that client; the custodian selector is not a client selector.

Render runs `backend/entrypoint.sh`, which applies migrations and supervises the API
and worker. Render’s filesystem is ephemeral; canonical and derived objects must use
Supabase S3 storage.

For local verification, `docker compose up -d --build` starts PostgreSQL, MinIO, an
idempotent private-bucket initializer, API, worker, and frontend. The API and worker
both use the existing S3 BlobStore with `CORPUS_S3_ENDPOINT_URL=http://minio:9000`,
`CORPUS_S3_REGION=us-east-1`, `CORPUS_S3_BUCKET=corpus-private`, and the Compose-only
`minioadmin` credentials. MinIO persists bytes in the named `minio_data` volume;
PostgreSQL persists metadata and object references. Retrieval/search is not part of
this slice.

## 1. Generate secrets locally

Run this locally and keep the output in a password manager or provider secret field:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Use the result only as `CORPUS_REVIEW_TOKEN`. Never commit it or place it in a
`NEXT_PUBLIC_*` variable.

## 2. Supabase

1. Create one Supabase project for this client: `<SUPABASE_PROJECT_NAME>` in region
   `<SUPABASE_REGION>`.
2. Open Storage and create a **private** bucket named `<CLIENT_BUCKET>` for this
   client. Never share it with another client deployment.
3. Create server-only S3 credentials for that project. Record the endpoint,
   region, access key, and secret key in the Render secret store only.
4. Obtain a long-running PostgreSQL connection string using the Supavisor
   session/transaction-compatible pooler, with `sslmode=require`:
   `postgresql://postgres.<PROJECT_REF>:<DB_PASSWORD>@<POOLER_HOST>:6543/postgres?sslmode=require`.
5. Apply migrations from `backend/migrations/` in filename order, or let Render run
   `python -m app.db.migrate` before starting traffic. Do not edit applied migration
   files; add a new numbered migration for future schema changes.

Supabase supplies these values to Render; it does not receive Vercel variables:

- `CORPUS_CLIENT_ID` — non-secret deployment identity for this client.
- `CORPUS_DATABASE_URL` — secret PostgreSQL URL.
- `CORPUS_S3_ENDPOINT_URL` — S3 endpoint for `<PROJECT_REF>`.
- `CORPUS_S3_REGION` — S3 region.
- `CORPUS_S3_BUCKET` — `corpus-private`.
- `CORPUS_S3_ACCESS_KEY` — server-only S3 access key.
- `CORPUS_S3_SECRET_KEY` — server-only S3 secret key.

## 3. Render

1. Connect the repository and select the intended branch.
2. Select the repository-root `render.yaml` Blueprint. Do not select
   `backend/render.yaml`; it is intentionally absent so there is one canonical
   Blueprint.
3. Review the service `corpus-backend` (`runtime: docker`, plan `free`). Its exact
   build settings are `rootDir: .`, `dockerfilePath: backend/Dockerfile`, and
   `dockerContext: .`.
4. Set these provider environment variables in Render:

   - `CORPUS_CLIENT_ID` (deployment identity; not a credential)

   Set the following values in Render's secret environment store:

   - `CORPUS_DATABASE_URL`
   - `CORPUS_S3_ENDPOINT_URL`
   - `CORPUS_S3_REGION`
   - `CORPUS_S3_BUCKET`
   - `CORPUS_S3_ACCESS_KEY`
   - `CORPUS_S3_SECRET_KEY`
   - `CORPUS_REVIEW_TOKEN`
   - `CORPUS_ALLOWED_ORIGINS` (set after the Vercel URL is known)

5. Confirm these non-secret Blueprint values remain unchanged:

   - `CORPUS_ENVIRONMENT=production`
   - `CORPUS_BLOB_STORE_BACKEND=s3`
   - `CORPUS_BLOB_STORE_ROOT=/tmp/corpus-blobs`
   - `CORPUS_MAX_UPLOAD_SIZE_BYTES=52428800`
   - `CORPUS_RATE_LIMIT_PER_MINUTE=120`
   - `PORT=10000` (Render may override the supplied port)

6. Deploy and wait for `/health` and `/ready` to pass. The worker must remain
   supervised in the same container; a worker exit intentionally fails the service.

The production configuration is rejected when the client identity, explicit database
URL, or private S3 backend configuration is missing.

The worker/runtime knobs are also supported by the backend and may be left at their
defaults in Render: `CORPUS_WORKER_POLL_SECONDS`, `CORPUS_WORKER_LEASE_SECONDS`,
`CORPUS_WORKER_PAGE_RETRY_LIMIT`, `CORPUS_WORKER_PAGE_DELAY_SECONDS`, and the local
failure-demo-only `CORPUS_WORKER_FAIL_PAGE_NUMBER`. `CORPUS_S3_STAGING_ROOT` is an
optional local staging override; do not use Render’s filesystem for durable data.

## 4. Vercel

1. Import the same repository into Vercel Hobby.
2. Set **Root Directory** to `frontend`.
3. Framework preset: **Next.js**.
4. Install command: `npm ci`.
5. Build command: `npm run build`.
6. Add these public variables only:

   - `NEXT_PUBLIC_API_BASE_URL=https://<RENDER_SERVICE>.onrender.com`
   - `NEXT_PUBLIC_REVIEW_TOKEN_REQUIRED=true`

Do not add database, S3, Render, or reviewer-token secrets to Vercel. Redeploy after
the Render URL is final.

## 5. CORS sequence

1. Create/import the Vercel project and note its production origin,
   `https://<VERCEL_PROJECT>.vercel.app`.
2. Set Render’s `CORPUS_ALLOWED_ORIGINS` to that exact origin, with no wildcard or
   trailing path. Include a custom production origin separated by commas only when
   it is actually used.
3. Deploy/restart Render and verify `/ready`.
4. Set Vercel’s `NEXT_PUBLIC_API_BASE_URL` to the Render HTTPS origin and redeploy
   Vercel.
5. Verify browser requests, preflight CORS, and canonical download from the Vercel
   origin. Update the Render allowlist before adding or changing a frontend domain.

## 6. Hosted verification

```powershell
curl.exe -i https://<RENDER_SERVICE>.onrender.com/health
curl.exe -i https://<RENDER_SERVICE>.onrender.com/ready
curl.exe -i https://<RENDER_SERVICE>.onrender.com/v1/custodians
curl.exe -i -H "X-Corpus-Review-Token: <REVIEW_TOKEN>" https://<RENDER_SERVICE>.onrender.com/v1/custodians
```

The unauthenticated Corpus request must return `401`; the token-authenticated request
must return `200`. In the Render shell, run:

```sh
python -m app.diagnostics
```

From a clean browser at `https://<VERCEL_PROJECT>.vercel.app`, enter the review token,
admit a safe PDF, confirm queued/processing/completed state, inspect source arrivals,
enrollment, checkpoints, and derived lineage, then download the canonical PDF. Check
the download hash against the source detail SHA-256. Admit the same bytes again and
confirm a new arrival without a duplicate source or active job.

## 7. Teardown and cleanup

1. Export any required review evidence and record the final source hashes.
2. Delete the Vercel project/deployment.
3. Delete the Render service and revoke its S3 credentials.
4. Delete the Supabase project or, if retaining it, remove the private bucket and
   database data according to the project’s retention policy.
5. Rotate the reviewer token and any credentials that were shared during review.

Do not use destructive migration rollbacks. Canonical objects are immutable and this
POC has no production SLA; free-tier sleep/cold-start behavior is expected.

To provision a second client, repeat the full Supabase, Render, and Vercel setup with
new resources and credentials, set a new `CORPUS_CLIENT_ID`, and point the new frontend
only at the new Render service. There is intentionally no shared database, shared
bucket, runtime connection switching, or central control plane.
