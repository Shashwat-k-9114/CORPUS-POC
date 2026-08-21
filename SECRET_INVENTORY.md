# Secret inventory

These values are required only in provider secret stores or local untracked `.env` files:

- `CORPUS_DATABASE_URL` — Supabase PostgreSQL connection string with SSL.
- `CORPUS_S3_ACCESS_KEY`, `CORPUS_S3_SECRET_KEY` — Supabase Storage S3 credentials.
- `CORPUS_REVIEW_TOKEN` — reviewer access token shared out-of-band with Piyush Sir.
- `CORPUS_ALLOWED_ORIGINS` — deployed Vercel origin; not secret, but deployment-scoped.
- `NEXT_PUBLIC_API_BASE_URL` — public Render API URL.
- `NEXT_PUBLIC_REVIEW_TOKEN_REQUIRED=true` — public feature flag only; never place the token in a `NEXT_PUBLIC_*` variable.

No credentials, personal PDFs, canonical objects, or generated artifacts belong in Git.
