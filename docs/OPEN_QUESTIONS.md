# Open questions

| # | Question | Owner | Status |
|---|---|---|---|
| 1 | Which open-source license and copyright holder? (Existing `LICENSE` is MIT; check whether the Hub/MDE requires one for the GitHub org. Apache-2.0 adds a patent grant.) | Viktoriia / Hub | Open — deferred 2026-11-19 |
| 2 | Wireframes for `design/wireframes/` (HTML export from artifacts) | Viktoriia | Needed before Phase 3 |
| 3 | Mississippi K–3 ELA standards file | Viktoriia | Needed before Phase 1 seed |
| 4 | Should `redistribution` / `derivatives` = "no" still allow approval? (Currently yes; they are only recorded.) | Hub / MDE | Open |
| 5 | Myth list in `api/seed/myths.json` is a draft. Needs SME review before teachers see it. | SME (Kritika?) | Open |
| 6 | `ingest/allowlist.json` has titles only. Need the official URLs / PDFs for the National Reading Panel report and the IES practice guide(s) to add. | Viktoriia | Open |
| 7 | ~~Bedrock model access (Titan V2).~~ Titan is not approved by the Hub boundary; embeddings run locally (ADR 0004). | Viktoriia | Closed 2026-11-20 |
| 8 | `nrp_2000` (src_0010) is rejected but the curated list says ready. Viktoriia will re-open it with the new button (reason required) and approve it. | Viktoriia | In progress |
| 9 | No-derivatives decision for CC BY-NC-ND sources (src_0084, src_0096; `pennell_2024` src_0083 is rejected). Re-opened, kept `quote_only`, excluded from retrieval until decided. | Aidan | Open (waiting on Aidan) |
| 10 | License sign-off for Put Reading First, NSW review and the REL PLC guide. Left as candidates with a note. | Aidan | Open (waiting on Aidan) |
| 11 | ~~Two curated entries had no URL.~~ Added 2026-11-19. | Viktoriia | Closed |
| 12 | ~~Evidence-label rule.~~ Decided 2026-11-19: WWC ratings map Strong/Moderate/Minimal to Very sure/Fairly sure/Not sure yet; other government guides never raise the label; count independent evidence. See DECISIONS.md. | Team | Closed |
| 13 | ~~Confirm label rule additions.~~ Decided 2026-11-19, see DECISIONS.md. | Viktoriia | Closed |
| 14 | Three interpretations of mine on the label rule (disagreement cap applies to the whole label; several small agreeing studies stay at Not sure yet; Phase 2 verifier decides what "contradicts"). See DECISIONS.md. | Viktoriia | Open |
| 15 | **Org SCP (id withheld) explicitly denies `bedrock:InvokeModel` for both models the `StorefrontModelBoundary` allows:** Haiku 5.5 (`us.anthropic.claude-haiku-5-5`) and Sonnet 4.5 (`us.anthropic.claude-sonnet-4-5-20250929-v1:0`), tested in us-east-2 on 2026-11-20. Until it is lifted, no Claude call can succeed and the Q&A engine cannot be run end to end. Ask the Hub to exempt these two models (and say which regions). Regions are not being probed. | Viktoriia -> Hub | Open |
| 16 | The Hub boundary allows no embedding model. We run BAAI/bge-small-en-v1.5 locally (ADR 0004). Confirm the Hub accepts this, and whether the deployed API (App Runner) may download the model or must ship it in the container image. | Viktoriia -> Hub | Open |
