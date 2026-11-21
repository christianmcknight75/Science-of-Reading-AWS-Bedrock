# ADR 0005: Q&A engine (built against fake model clients, switched off)

Status: accepted (2026-11-20)

## Decision
Pipeline in `api/app/`: `redact` (Presidio + regex) -> `router` (rules, no model) -> `retrieval` (vector + full-text, reciprocal rank fusion, grade/topic/recency filters, similarity threshold, max 3 passages per source) -> `prompt` -> `llm` (Bedrock Converse, forced tool output) -> `verifier` -> `evidence` (existing, rule-based label) -> `myths` -> `engine` -> `query_log`. Endpoint: `POST /api/ask` (`qa.py`).

- **Verifier**: (a) a cited id that was not retrieved is a fabricated citation and the claim is dropped; (b) each claim carries a quote that must appear verbatim in a cited passage (only whitespace and typographic quote/dash variants are treated as equal; case counts; at least 3 words); (c) one batched model call returns supported / unsupported / contradicted per claim. It fails closed: no verdict means the claim is removed. If fewer than half the claims survive, or none, the engine answers "I found related research but could not build an answer the sources support".
- **Contradicted** claims feed `evidence_result(contradicts=True)`, so the label is capped at "Not sure yet" and `mixed` is set (closes the "who decides contradiction" part of open question 14).
- **Myths**: the correction is shown only when the myth has `passage_ids` (so it always carries a citation). Unlinked myths are logged (`myths_without_sources`) so we know which sources are missing.
- **Safety rails**: kill switch `QA_ENABLED` defaults to **false**; per-user rate limit (default 6/min, in memory per instance); `max_tokens` caps; passages are delimited, escaped and declared untrusted; Guardrails attaches when `GUARDRAIL_ID` is set (not created yet; Phase 5).
- **Logging**: `query_log` gets only the redacted question, retrieved ids, answer text, label, latency and a JSON of verifier results and token counts.
- **No streaming yet**: the verifier must finish before anything is shown, so the endpoint returns the whole answer. Streaming can later carry progress states, not unverified text.
- **Evals** (`evals/`): `--mode retrieval` is free and is what `make eval` runs; `--mode fake` tests the plumbing; `--mode live` also runs a plain-Claude baseline and needs both `--live` and `SOR_ALLOW_LIVE_MODEL_CALLS=1`.

## Consequences
- Nothing has been run against a real model: both allowed models are blocked by the org SCP (open question 15). Prompt quality, label expectations and the similarity threshold are unproven until a live run.
- Similarity alone does not separate off-topic questions (fractions and photosynthesis reach 0.72-0.75 against a 0.70 threshold). The model's `answerable` flag and the verifier are the second line; the live eval must show they hold.
- The API Docker image does not yet contain `config/models.yaml`, the spaCy model or the BGE model files (Phase 5).
