# ADR 0002: Knowledge layer and approval gate

Status: accepted (2026-11-19)

## Decision
- Schema is managed with Alembic using plain SQL (pgvector `vector(1024)` + HNSW cosine index; generated `tsvector` column + GIN index).
- Approval is enforced in three places, so a bug in one cannot let unlicensed text in:
  1. the database: a `CHECK` constraint refuses `status = 'approved'` unless reviewer, date, license, attribution, license snapshot and checklist are all present;
  2. the admin API: approving needs copy/store, AI use, excerpt display and third-party review all confirmed;
  3. the ingestion code: `upsert_passages` raises `PermissionError` for any source that is not approved.
- `redistribution` and `derivatives` are recorded on the checklist but do not block approval (they matter for the handoff, not for teacher-facing excerpts). Confirm with the Hub.
- Admin routes require the Cognito `admin` group. Auth fails closed; `AUTH_MODE=dev` exists for local Docker only.
- License snapshots are stored on local disk for now (`data/local/license_snapshots`, git-ignored). Phase 5 moves them to a private, KMS-encrypted S3 bucket.
- Embeddings: **superseded by ADR 0004** (local BGE, 384 dims). Originally Titan V2 at 1024 dims. A deterministic stub is used in tests.

## Why
CLAUDE.md rule 4: only licensed sources. A government proof of concept needs the gate to be hard to bypass and easy to explain.
