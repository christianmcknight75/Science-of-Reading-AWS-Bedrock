# ADR 0004: Local embeddings (BAAI/bge-small-en-v1.5, 384 dims)

Status: accepted (2026-11-20)

## Decision
- Passages and questions are embedded locally with BAAI/bge-small-en-v1.5 (384 dimensions) through `fastembed` (ONNX, CPU). Passages are embedded as is; questions get BGE's search-instruction prefix.
- `passages.embedding` is `vector(384)` (migration 0008, HNSW cosine index rebuilt). The model, its dimensions and the query prefix come from `config/models.yaml`.
- The Titan embedder and its hard-coded default ID are removed.

## Why
The Hub's IAM permissions boundary (`StorefrontModelBoundary`) allows only two Claude models and no embedding model, so Titan Text Embeddings V2 (the original choice) cannot be called. Local embedding costs nothing per call and keeps passage text off the network.

## Consequences
- BGE-small reads about 512 tokens. Passages above that (the upper end of the 300-500 word target) are truncated for embedding only; the full text is stored, shown and searched by the full-text index. Hybrid search covers the gap.
- Changing the model again means a migration and re-embedding (`sor-ingest embed`, about 2 minutes on a laptop CPU).
- The API container must contain the model (or download it at start). See open question 16.
- Supersedes the embedding line in ADR 0002 and in CLAUDE.md's stack table (which still says Titan; update it).
