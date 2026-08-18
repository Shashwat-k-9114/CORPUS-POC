# CORPUS — Project Overview

## What this document is

This describes what Corpus *is*, as a product: its purpose, current scope, and status.
It is not a changelog — for what has actually been built session-by-session, see
`BUILD_LOG.md`. For technical/product decisions and their rationale, see `DECISIONS.md`.
For itemized requirements, see `REQUIREMENTS.md`.

## Purpose

Corpus is intended to become a document-understanding and finding system: given a
document, understand its structure, let a user search/find information within it, and
return findings with reliable provenance back to the exact location in the source
document they came from.

This repository (`corpus-poc`) is **not** that final system. It is the first
independently deployable prototype — an interactive product validation layer built on
top of earlier research (`../poc-01/`, treated as read-only, frozen experimental
evidence).

## Problem statement

Long documents (financial reports, filings, technical documents) bury information the
reader needs inside dozens or hundreds of pages. Getting from "the document" to "the
specific fact, with confidence about where it came from" is currently manual and slow.
Corpus aims to make that traceable and fast — but only once we know, from a real
stakeholder using a real (if small) product, what "traceable and fast" actually needs to
mean.

## Why a prototype, and why now

Earlier work (`../poc-01/`) ran isolated extraction experiments (pdfplumber, PaddleOCR,
in-progress Marker investigation) and produced valuable evidence about what native-PDF
text extraction can and cannot recover. But that work has no interactive surface — no
one outside the experiments can open a document and see what was found. The stakeholder
has asked for small, deployable, testable increments instead of a large architecture
built in isolation. This repository exists to close that loop:

RESEARCH → BUILD SMALL → DEPLOY → TEST → GET FEEDBACK → MODIFY → DEPLOY AGAIN

## Current scope (v1 / this prototype)

The first version establishes the fundamental Corpus interaction loop for **native PDFs
only**:

PDF upload → processing → native text-layer extraction → page-level and word-level
representation with bounding boxes → visual inspection of the source page alongside the
extracted content → provenance from extracted text back to its page and location.

In scope for v1:
- Native PDF upload (text-layer PDFs; not scanned/image-only)
- Page-level extraction (text, dimensions, word/char counts)
- Word-level regions with bounding boxes (pdfplumber baseline, per `[[dec-003-extraction-engine]]`)
- Visual page inspection (rendered page image) alongside extracted content
- Minimal REST API (JSON) between a Next.js frontend and a FastAPI backend
- Local development workflow and a deployable, testable URL

## Explicitly out of scope for v1

- OCR / scanned document support (PaddleOCR, Marker, or any OCR engine)
- Semantic search, vector search, embeddings, RAG
- Table structure extraction (pdfplumber's default table detection was shown unreliable
  in Experiment 1 and is not part of this prototype's extraction surface)
- Persistent database / multi-document library / multi-user accounts
- Authentication (unless the chosen deployment platform requires it to function at all)
- Agentic workflows, multi-service/microservice architecture

These are not rejected forever — they are deliberately deferred until a working
end-to-end slice exists and a stakeholder has used it. See `REQUIREMENTS.md` for
non-requirements tracked explicitly.

## Target users / stakeholder

A single internal stakeholder evaluating whether the Corpus interaction model (upload →
inspect → trust the provenance) is worth building further. Not yet built for external
end users, multiple concurrent users, or production traffic.

## Current user journey (v1 target)

1. User opens the deployed web app.
2. User uploads a native-text PDF.
3. App processes the document and shows clear progress/status.
4. User views the document page-by-page (rendered image).
5. User views extracted text/word regions for the page they're viewing.
6. User can see where a given piece of extracted text came from (page, bounding box).

## Current capabilities

As of this document's last update: **none yet implemented.** This session completed
Phase 0 (inspection/planning) and the documentation foundation only. No backend or
frontend application code exists yet. See `BUILD_LOG.md` for the authoritative,
up-to-date implementation status.

## Current limitations

- No application code exists yet (pre-Phase 2).
- Even once built, v1 will only handle native-text PDFs, not scanned documents.
- No persistence: extraction results are not expected to survive a backend restart in
  v1 (see `[[dec-004-no-database]]`).
- Table structure will not be extracted or represented in v1.

## Roadmap (directional, not committed)

- v1 (this prototype): native PDF upload → word-level extraction with provenance →
  document viewer. Phases 1–10 as defined in the project brief.
- Possible v2 directions (not started, not committed): scanned-document support via one
  of the researched OCR paths, table structure representation, persistence for
  multi-document use, in-viewer highlighting driven by clicking extracted text.

## Success criteria for v1

- A stakeholder who has never seen the source code can open the deployed URL, upload a
  native PDF, and correctly understand what was extracted and where it came from.
- The full acceptance checklist in the original project brief is satisfied and honestly
  reported (implemented vs. tested vs. deployed vs. verified are tracked separately).

## Current status

**Phase 0 complete: repository inspected, minimal architecture proposed, documentation
foundation created.** Phase 1 (repository setup/doc system) is now substantially done as
part of this same session. Phase 2 (minimal backend) has not started. See `BUILD_LOG.md`
for the authoritative state.
