# SoR Assistant — Full Project Plan (saved verbatim from Viktoriia)

Future sessions: read `CLAUDE.md`, this file, and `docs/DECISIONS.md` first. Record every new decision in `docs/DECISIONS.md`.

## Status (updated 2026-11-20)
Branch `viktoriia/foundation`. 2026-11-20 update: embeddings are now local BGE-small (384), all 1,619 embedded; both allowed Claude models are blocked by an org SCP (OPEN_QUESTIONS 15). Phases 0 and 1 are done. **Phase 2 is started but not built: only the data preparation is finished.**

**Done for Phase 2 (data side)**
- All 14 approved sources are parsed into 1,619 passages (300-500 words, hard max 600, short ones merged, section heading first, PDF page + printed page label, grade for the per-grade src_0123). Embeddings are the **stub** embedder only: they must be replaced with Titan V2 (`sor-ingest process --embedder titan --all`) before retrieval can work.
- Evidence ratings verified by Viktoriia for the four WWC guides (src_0011, src_0120, src_0125, src_0126); `retrievable_passages` shows a rating only for verified sources. WWC "Low" is stored as Minimal (ADR 0003).
- Audit trail: status changes, identity corrections (migration 0005) and rating verification are all logged in `source_audit`. Migrations 0005-0007 are applied locally.
- Held out of retrieval until Aidan signs off: Put Reading First, REL PLC guide, NSW review, the two CC BY-NC-ND papers (src_0084, src_0096).
- AWS: SSO profile `sor-dev` works. The Hub's policy blocks listing Bedrock models, so model IDs come from the docs and are unconfirmed (see DECISIONS.md, 2026-11-20).

**Built 2026-11-20 against fake model clients (ADR 0005), never run live:** redaction, router, hybrid retrieval, prompt, Converse client, verifier, label wiring, myths, rate limit, kill switch (off), query_log, eval harness. Remaining: live run (blocked by SCP, OPEN_QUESTIONS 15), Guardrails creation (Phase 5), SME-reviewed eval set. The list below is what was not started before this.

**Not started before 2026-11-20**
Presidio redaction, router, hybrid retrieval over `retrievable_passages` only, relevance threshold, prompt builder, Converse call with claims-to-passage_ids output, verifier (cited ids, exact quotes, claim support), rule-based evidence label wiring, myth check, Guardrails, rate limits and kill switch, `query_log`, `evals/questions.yaml`, eval harness and `make eval`.

**Next steps, in order**
1. Viktoriia approves 3 tiny test calls to confirm the Haiku, Sonnet and Titan IDs; put them in config.
2. Cost estimate for embedding 1,619 passages (~0.7M tokens, expected 1-2 cents) -> approval -> real embeddings.
3. Build the engine pieces above, then a first eval set (team sample questions in `docs/reference/` plus drafted myth and no-research cases, marked not SME-reviewed), cost estimate before any eval run.
4. Stop at the end of Phase 2 with the first eval report.

**Known data issues to revisit:** src_0123 has ~29 short passages (how-to steps, reminder boxes); the glossary skip is global (also skips src_0125's glossary); page labels are PDF-provided where they exist.

---

You are the lead engineer on the SoR Assistant ("Reading Helper"), a research-grounded science-of-reading assistant
for K–3 teachers, built for the Mississippi Department of Education. Read `CLAUDE.md` first: it holds the rules,
approved stack, data model, answer format, design system, and quality gates. Also read `docs/AWS_SETUP_SAFELY.md`,
everything in `docs/reference/` (proposal, meeting insights, architecture sketch, license checklist), and the wireframes in
`design/wireframes/`.

About me: I'm Viktoriia, the team's AI & Systems lead. I'm strong in Python and CS fundamentals but **new to AWS**.
Explain every AWS step in plain language before you run it. I'll be reviewing your work and showing it to the team,
so keep commits clean and explained.

## How we work
- Work in the phases below. **At the end of each phase, stop**, summarize what you built, show how to run and test it,
  list open questions, and wait for my "go".
- Use a task list, small commits, and one PR per feature. Write an ADR in `docs/adr/` for each significant decision.
- Use the installed skills where they fit: `aws-core` (CDK, Bedrock, IAM, Cognito, billing), `engineering`
  (architecture, code-review, testing-strategy, documentation, deploy-checklist), `aws-agents-for-devsecops`
  (security scans before merging), `design:accessibility-review`, `design:ux-copy`, and `frontend-design`.
- **AWS safety:** never deploy, destroy, or create cloud resources without first showing `cdk diff`, a monthly cost
  estimate, and getting my typed "approved". Never create anything on the "burns money" list in
  `docs/AWS_SETUP_SAFELY.md`. Use AWS profile `sor-dev`. Never read, print, or store secret values.
- If a requirement is ambiguous or conflicts between documents, `CLAUDE.md` wins. If it's still unclear, ask me and
  don't guess. Track open sponsor questions in `docs/OPEN_QUESTIONS.md`.
- Everything must work locally first (Docker Compose: Postgres + pgvector, API, web) before anything touches AWS.

## Phase 0 — Repo foundation
- Monorepo: `web/` (React + Vite + TS + Tailwind), `api/` (FastAPI), `ingest/` (pipeline), `infra/` (CDK),
  `evals/`, `docs/`, `design/`.
- Docker Compose for local dev; `Makefile` with `make dev`, `make test`, `make eval`, `make lint`.
- Tooling: ruff, mypy, pytest, eslint, prettier, tsc, pre-commit, gitleaks; GitHub Actions CI running all of it.
- `.gitignore` covering `.env*`, credentials, and local data. A `SECURITY.md` and a `LICENSE` (ask me which open-source license).
- Design tokens from `CLAUDE.md` in `web/src/styles/tokens.css` + Tailwind config. Fonts self-hosted (Lexend, Atkinson Hyperlegible).
**Stop and report.**

## Phase 1 — Knowledge layer + ingestion
- Postgres schema and migrations (Alembic) for `sources`, `passages`, `standards`, `myths`, `grapheme_scope`, `query_log`.
  pgvector (1024-dim, HNSW index) + tsvector with a GIN index.
- Ingestion CLI: fetch candidates from ERIC + OpenAlex (open-access, peer-reviewed, last 10 years, plus the foundational
  allow-list) → status `candidate`. Nothing is parsed or embedded until a source is `approved` with a completed license record.
- Admin page (Cognito admin group only): review queue implementing the license checklist as a form (identify → license →
  allowed uses → third-party content → attribution → archived license snapshot upload → decision, reviewer, date).
- Parse with PyMuPDF → 300–500-word passages that keep section and page → embed with Titan V2 → upsert with versions.
- Seed: Mississippi K–3 ELA foundational standards (from the file I provide), an initial myth list (three-cueing/MSV,
  guessing from pictures, learning styles, leveled-text-only for beginners, etc., each tied to passages once the corpus exists).
- Locally, a stub embedder lets tests run without AWS.
**Stop and report.**

## Phase 2 — Q&A engine (the core)
Pipeline: PII redaction (Presidio) → router → hybrid retrieval (vector + full-text, reciprocal rank fusion, filters on grade/topic/recency)
→ relevance threshold → prompt builder → Claude via Bedrock Converse (streaming, tool/JSON output with claims → passage_ids)
→ **verifier** → evidence label → myth check → response.
- Verifier: (a) reject any cited id not in the retrieved set; (b) every quoted span must appear verbatim in its passage;
  (c) a fast model check that each claim is supported by its passage; unsupported claims are removed, and if too little remains,
  fall back to the honest "not enough research" reply.
- Retrieved text is untrusted data: delimit it and instruct the model never to follow instructions found inside passages.
- The evidence label is computed by code from source types and counts, not by the model.
- Bedrock Guardrails for PII + denied topics (student-specific decisions, retention/promotion, product endorsements,
  teacher evaluation).
- Rate limits, `max_tokens`, a kill-switch flag, and `query_log` with redacted text only.
- Eval harness in `evals/`: run the question set (start with the team's sample questions in `docs/reference/`), compute
  fabricated-citation rate, quote-match, label correctness, honest-no-research rate, latency; compare against plain Claude
  with no retrieval. Output a Markdown + JSON report. Wire `make eval` and an on-demand CI job.
**Stop and report with the first eval results.**

## Phase 3 — Teacher web app (v5 wireframes)
- Screens: Home (Teaching / Training + "Just ask"), Answer, Make a story, Tomorrow's groups → group plan, Why is a kid stuck?,
  My training → topic → plan, 1-minute refreshers, Text size & read aloud settings, Class board (projector view),
  No-research state, loading state. Behavior and Progress exist only behind feature flags that are OFF.
- Answer UI follows the format in `CLAUDE.md`: evidence label first, "Research says" vs "Idea for your class",
  numbered citations opening a sources panel with the exact passage and page.
- Streaming responses with a calm loading state; mobile-first; works with keyboard and screen readers.
- Persistent advisory disclaimer + "content last updated" date in the footer of every screen.
- Cognito sign-in (invite-only). No student names anywhere. Group labels are free text like "Group A".
- Playwright end-to-end tests + axe accessibility checks in CI. Run `design:accessibility-review` on each screen.
**Stop and report with screenshots.**

## Phase 4 — Teaching tools
1. **Decodability checker** (pure code, fully unit-tested): CMU Pronouncing Dictionary + grapheme-phoneme rules +
   `grapheme_scope`. Input: taught graphemes + heart-word list. Output: each word decodable yes/no with the reason.
2. **Make a story**: the model drafts → the checker validates every word → retry/repair up to N times → never show a story
   containing non-decodable words (highlight any the teacher adds herself). Printable PDF.
3. **Lesson plan check**: upload PDF/DOCX/text → split into sections → rubric + myths + MS standards + retrieval → per-section
   margin notes (research-backed / mixed / change this) the teacher can accept or dismiss. Developmental tone, no scores.
4. **Activity generator** (syllables, blending, segmenting, Elkonin boxes): research basis shown, printable, projector view.
5. **Why is a kid stuck?**: error description → pattern match against the error-pattern list → cited next steps.
6. **My training**: pick a PD topic → this week's 3-step plan + 1-minute refreshers, all cited.
**Stop and report.**

## Phase 5 — AWS deployment (only after my go)
- Before writing any CDK, walk me through `docs/AWS_SETUP_SAFELY.md` Steps 0–5 and check each one is done
  (budgets with credits unchecked, the brake action, anomaly detection, Bedrock model access, SSO profile).
- CDK stacks: Network (VPC, private subnets, Bedrock + Secrets Manager interface endpoints, **no NAT**), Data (RDS
  t4g.micro, encrypted, private, automated backups 7 days), Auth (Cognito), API (App Runner + VPC connector, ECR),
  Web (S3 private + CloudFront OAC + security headers + WAF only if cost is OK'd), Observability (log retention 30 days,
  CloudTrail, alarms on errors and on Bedrock spend), CI (GitHub OIDC deploy role, least privilege).
- `cdk-nag` (AwsSolutions pack) must pass or each suppression must be justified.
- Show `cdk diff` + cost estimate → wait for "approved" → deploy → smoke test → report the URLs.
- Run the AWS Security Agent scan and the `aws-well-architected-review` skill (security + cost pillars) and fix the findings.
**Stop and report.**

## Phase 6 — Hardening and handoff
- Load test lightly (50 questions/day scenario), check p95 latency, tune model choice by eval results.
- `docs/HANDOFF.md`: architecture diagram, how to add a paper, how to add another state's standards, how to run evals,
  how to deploy/destroy, costs, data handling & retention (Public Records Act), known limitations.
- Demo script for the showcase: Q&A with citations → myth caught → honest no-research → decodable story → lesson check,
  plus a side-by-side vs plain chatbot from the eval report.

Start with Phase 0. Before writing code, give me your understanding of the project in 10 bullet points and list
any questions.
