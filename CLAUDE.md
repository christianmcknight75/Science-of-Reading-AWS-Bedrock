# SoR Assistant ("Reading Helper") — Project Brief for Claude

Claude reads this file at the start of every session. Follow it. If a request conflicts with it, stop and ask.

## What this is
A research-grounded professional-learning assistant for **K–3 teachers** (Mississippi pilot; built so it can go
nationwide later). Client: Mississippi Department of Education via the USM AI Innovation Hub. Team ADA.
It helps teachers turn science-of-reading PD into classroom practice. **Teachers are the only users. Students never use it.**

It is a government proof of concept. Quality bar: accurate, accessible, secure, cheap to run, easy to hand off.

## Non-negotiable rules
1. **No source, no claim.** Every factual statement in an answer must cite a `passage_id` that was retrieved for that request.
   The verifier rejects anything else. Fabricated citations must stay at zero.
2. **No student data, no PII, no real teacher artifacts.** Strip names/schools before logging or calling the model.
   Never build features that store student names, scores, or assessment results.
3. **Advisory only.** Persistent disclaimer + "content last updated" date on every output. Never rate or evaluate the teacher.
4. **Only licensed sources.** A source enters the corpus only after the license checklist is approved
   (copy/store, AI use, excerpt display, redistribution, derivatives, attribution recorded, license snapshot archived).
   No web scraping. Use ERIC / OpenAlex / Semantic Scholar / PubMed Central APIs with open-access filters.
   No LETRS or other proprietary PD content.
5. **Recency:** new peer-reviewed studies from the last ~10 years; a small allow-list of foundational docs
   (National Reading Panel 2000, IES practice guides) is kept regardless of age.
6. **Out of scope:** promotion/retention decisions, curriculum or product endorsements, teacher evaluation,
   classroom audio/video, integration with district systems.
7. **Accessibility:** WCAG 2.1 AA is the legal standard (ADA Title II). Not optional.
8. **Cost:** never create NAT Gateways, Bedrock Provisioned Throughput, OpenSearch Serverless, SageMaker endpoints,
   or anything always-on that is not in the approved stack below. Never run `cdk deploy`, `cdk destroy`, or any
   command that creates/deletes AWS resources without showing `cdk diff` + a monthly cost estimate and getting
   explicit approval from Viktoriia in chat.
9. **Secrets:** no keys or passwords in code, `.env` files committed, or logs. The repo is public (open source).

## AWS account facts
- Account `USM-SOR-ADA-32`, provided by Mississippi ITS through **Innovation Sandbox on AWS**. It is a *leased* sandbox:
  it has a budget cap and an end date, and when either is reached the account can be **frozen or wiped** (AWS Nuke deletes everything).
- So: all code lives in GitHub, all infrastructure lives in CDK, and back up the database + corpus to the repo/release artifacts regularly.
  Nothing important may exist only in AWS.
- Use the `msaih_IsbUsersPS` role day to day. Region: **us-east-2 (Ohio)** unless the Hub says otherwise; call Claude via
  Bedrock cross-region inference profiles (`us.` model IDs). The Hub's boundary policy allows only two Claude models and no embedding model.
- Budgets and root-account security are managed by the Hub; don't try to change them. Check spend weekly in Cost Explorer.

## Approved stack (all in one AWS account, region us-east-2)
| Layer | Choice |
|---|---|
| Frontend | React + Vite + TypeScript + Tailwind; Radix primitives (or shadcn/ui) for accessible components; static build on S3 + CloudFront |
| API | Python 3.12, FastAPI, async, streaming responses; container on AWS App Runner |
| LLM | Claude on Amazon Bedrock via `boto3` Converse API. Only models allowed by the Hub's `StorefrontModelBoundary` policy (Haiku 5.5, Sonnet 4.5). Model IDs come from `config/models.yaml`, never hard-coded. Currently Sonnet 4.5 for generation and claim check; Haiku 5.5 is the intended fast model once the org SCP stops blocking it (see `docs/OPEN_QUESTIONS.md` 15). |
| Embeddings | Local `BAAI/bge-small-en-v1.5` (384 dims) via fastembed; no Bedrock embedding model is approved (ADR 0004). Model and dimensions come from `config/models.yaml`. Switching means a migration and re-embedding. |
| Database | Amazon RDS PostgreSQL (db.t4g.micro, 20 GB gp3, single-AZ for PoC) + pgvector + tsvector hybrid search |
| Network | App Runner VPC connector → RDS in private subnets. Reach Bedrock/Secrets Manager through **VPC interface endpoints**, not a NAT Gateway. |
| Auth | Amazon Cognito user pool, invite-only, MFA available |
| Safety | Bedrock Guardrails (PII + denied topics) + Microsoft Presidio pre-filter |
| Secrets | AWS Secrets Manager; KMS encryption at rest everywhere |
| IaC | AWS CDK (TypeScript or Python — pick one and stay with it). Everything is in code so `cdk destroy` removes it all. |
| CI/CD | GitHub Actions; deploys via GitHub OIDC role (no long-lived AWS keys) |
| Observability | CloudWatch logs with 30-day retention; CloudTrail on |
| PDF parsing | PyMuPDF (GROBID only if section splitting is poor) |
| Lesson-plan upload | PDF (PyMuPDF), DOCX (python-docx/mammoth), plain text |

Older team docs mention Next.js/Vercel/Render/Supabase. **Superseded** by the table above (AWS credits, one security boundary). (BGE embeddings are back, run locally: ADR 0004.)

## Data model (keep these names)
- `sources`: source_id, title, authors, year, doi/eric_id, url, pdf_url, license, license_snapshot_url, attribution,
  source_type (practice_guide | meta_analysis | study | foundational), topics[], grades[], approved_by, approved_at, version
- `passages`: passage_id (`src_0001_p012`), source_id, section, page, text (300–500 words), embedding, tsv, version
- `standards`: standard_id (`MS_ELA_RF_K_2`), state, grade, domain, description — **swappable per state**
- `myths`: myth_id, name, cue_patterns[], sor_correction, passage_ids[]
- `grapheme_scope`: ordered phonics scope & sequence used by the decodability checker
- `query_log`: id, ts, feature, redacted_question, retrieved passage_ids, answer, evidence_label, latency_ms, verifier_result, feedback
  (Mississippi Public Records Act: logs are records — no PII, defined retention)

## Answer format (same everywhere)
1. **Evidence label first** (plain words, expert word small): Very sure / Fairly sure / Not sure yet / No research found.
   Rule-based, not model-guessed: 2+ practice guides or reviews agreeing = Very sure; 1 good study = Fairly sure; else Not sure yet.
2. **Short answer**: 2–3 plain sentences (~6th-grade reading level), numbered citations.
3. **Try it in class**: up to 3 steps with minutes.
4. **Watch out for**: relevant myth, if any.
5. **Sources panel**: title, year, type, the exact passage used, page.
Visually separate **"Research says"** (cited) from **"Idea for your class"** (our suggestion based on research; never presented as research).
No retrieval above threshold → honest "no research" reply and offer what we *can* help with. Never guess.

## Features (build in this order)
1. Ingestion pipeline + admin source review (license checklist as a form)
2. Q&A with citations + verifier (claim-level support check AND exact-quote match) + evidence label + myth detector
3. **Decodable text / "Make a story"**: teacher picks taught graphemes; generator may only use words whose
   phonemes map to taught graphemes (checked with CMU Pronouncing Dictionary + grapheme rules, in plain code — no AI guessing);
   high-frequency/heart words allowed only from an explicit list.
4. Lesson plan check: per-section margin notes (research-backed / mixed / change this), mapped to MS standards
5. Activity generator (syllables, blending, segmenting) with printable PDF + projector "class board" view
6. "Why is a kid stuck?" error-pattern helper (Kritika's error list + retrieval)
7. My training → turn a PD topic into this week's plan; 1-minute refreshers
**Parked until sponsor confirms (feature-flagged OFF):** Behavior coach, group Progress tracking, coaching scenario simulation.
(Behavior is outside SoR scope in the proposal; Progress numbers may count as assessment data.)

## Design system (from the team's v5 wireframes)
- Fonts: **Lexend** (headings), **Atkinson Hyperlegible** (body), 17px base, line-height 1.5
- Colors: bg `#F4F6FA`, surface `#FFFFFF`, ink `#15233A`, muted `#4A5872`, border `#D9DFEA`,
  primary `#1F4E8C` (hover `#163A69`), highlight `#F5C842`, notice bg `#FDF3D3` / text `#4A3700`
- Targets ≥48px (64px in classroom/projector mode); one main action per screen, max 3 choices; status never by color alone
- Top nav: Home | Teaching | Behavior (flagged) | Training | Text size & read aloud
- Settings: text size, high contrast, reduced motion, read-aloud, English/Spanish (Spanish later)
- No emoji icons; stroke SVG icons with text labels; real `<button>`/`<a>`/`<label>`
- Product name in UI: "Reading Helper"
Wireframes: `design/wireframes/` (exported from the team canvas). Match them; where they conflict with these rules, rules win.

## Quality gates (CI must pass before merge)
- Eval set (`evals/questions.yaml`, 20–30+ SME-reviewed K–3 questions incl. myth checks and no-research cases):
  fabricated citations = 0, quote-match = 100%, no-research cases answered honestly, latency p95 < 8s
- Unit tests for decodability checker, verifier, evidence-label rules, PII redaction
- axe-core / Playwright accessibility checks: 0 serious/critical violations
- Lint/type checks (ruff, mypy, eslint, tsc); dependency + secret scanning (Dependabot, gitleaks)

## Working style
- Small PRs, one feature each. Write an ADR in `docs/adr/` for every significant choice.
- Explain AWS steps in plain language before doing them — Viktoriia is new to AWS.
- Keep `README.md` and `docs/HANDOFF.md` current enough that MDE could run it without us.
