# Five-minute reviewer walkthrough

1. Start the production-shaped local stack with `docker compose up -d --build` and
   open <http://localhost:3000>. Hosted reviewers first enter the supplied review
   token in the session-only access prompt.
2. In **Admit sources**, choose the seeded demo custodian/corpus and upload a small
   safe fixture PDF. The receipt shows source, canonical, arrival, enrollment, and
   queued-job identities. No extraction occurs in the request.
3. Open **Register** and **Processing monitor**. The worker advances page checkpoints
   asynchronously; stop and restart `worker` to demonstrate durable resumption.
4. Open source detail and download the canonical PDF. The downloaded bytes remain
   identical after an API restart. The derived inspector shows representation → page
   → job → source → canonical lineage and retains the existing bounding-box viewer.
5. Admit the same fixture again. The source/canonical/enrollment are reused while a
   second arrival records repeated delivery evidence and no redundant active job is
   created. A one-byte change produces a distinct source.

The demo uses repository-owned fixtures only. Limitations are explicit: free-tier
hosted services may sleep, Render has no durable local disk, and Supabase S3 storage
must be private. OCR expansion, embeddings, vector databases, RAG, LLM findings, and
distributed queues are not part of this POC.
