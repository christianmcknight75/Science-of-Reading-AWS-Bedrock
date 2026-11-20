# Decisions log

Future sessions: read this file at the start. Append every new decision (date, question, answer, how it was interpreted).
Decisions are Viktoriia's unless noted.

## 2026-11-19 — Phase 0 kickoff questions

| # | Question | Answer | Interpretation / action |
|---|---|---|---|
| 1 | Folder layout: (a) Phase 0 names `web/ api/ ingest/ infra/` + `git mv` source_search into `ingest/`, or (b) keep team names | "Terraform is fine" | Read as: removing the empty placeholder and Terraform folders is fine. Go with (a). **Confirm if that reading is wrong.** |
| 2 | `backend/requirements.txt` | Delete it | Delete; real deps go in `api/pyproject.toml`. |
| 3 | License | Skip for now | No LICENSE change. Tracked in `docs/OPEN_QUESTIONS.md` (choose license + copyright holder; check Hub/MDE requirement). Existing MIT `LICENSE` stays untouched meanwhile. |
| 4 | Commit CLAUDE.md, AWS doc, docs/reference? | Commit none of them; only for Claude's use | Add `CLAUDE.md`, `.claude/`, `docs/AWS_SETUP_SAFELY.md`, `docs/reference/`, `docs/PLAN.md`, `docs/DECISIONS.md` to `.gitignore` (kept locally only). |
| 5 | CDK language | Python | `infra/` is Python CDK. ADR to follow. |
| 6 | Python/JS tooling | OK | uv for Python, npm for web, Python 3.12 in Docker. |
| 7 | Wireframes | Ask when needed (Phase 3); user supplies HTML export from artifacts | Proceed without `design/wireframes/` for now. |
| 8 | Self-host Lexend + Atkinson Hyperlegible (SIL OFL) | "surels" (yes) | Self-host with license files. |

## Standing instructions
- Save all future decisions here.
- Full plan lives in `docs/PLAN.md`.

## 2026-11-19 — Commit attribution
- No "Co-Authored-By: Claude" or "Generated with Claude Code" lines in commits or PRs. Everything should look like Viktoriia's own work.

## 2026-11-19 — Phase 1 choices made without asking (change if you disagree)
- Approval rule: copy/store + AI use + excerpt display + third-party review must be ticked; redistribution and derivatives are recorded only. Attribution text and an uploaded license snapshot are required. See ADR 0002.
- Myth list is a draft of 6 myths pending SME review. Standards loader is ready (`python -m app.seed standards file.csv`, columns standard_id,state,grade,domain,description); waiting for the Mississippi file.
- Foundational allow-list entries have no URLs yet.

## 2026-11-19 — Curated sources loaded (`ingest/curated_sources.yaml`)
- Viktoriia supplied a curated list. `uv run sor-ingest curated` loads it (use `--dry-run` first). It replaces the old `allowlist` command and `allowlist.json` (removed).
- Rules I applied: `ready`/`verify` entries -> review-queue candidates, never auto-approved. `permission`/`quote_only` entries -> parked as `rejected` with an "ON HOLD" note, so they cannot reach the corpus. Decisions a human already made (approved/rejected) are never changed; only curation metadata is attached.
- Schema change (migration 0002): `government_guide` source type, plus `curated_id`, `publisher`, `jurisdiction`, `priority`, `used_for`, `foundational_allow_list`, `curation_status`, `curation_note`.
- Result on the local DB: 11 new candidates, 3 parked, 10 existing rows matched to curated entries. 7 approved sources stayed approved.
- Pending, for Viktoriia to decide: see OPEN_QUESTIONS 8-11.

## 2026-11-19 — Re-open, audit, holds, evidence label (Viktoriia)
1. **Re-open action.** Admin can re-open rejected -> candidate and approved -> candidate. A reason is required. Who, when, why are logged in the `source_audit` table. Source status is **never changed directly in the database**: a DB trigger refuses any status change that has no actor and reason, and writes the audit row itself (migration 0003). Approve/reject decisions are logged the same way. Claude must not run `UPDATE sources SET status` by hand.
2. **src_0084 and src_0096 (CC BY-NC-ND): no-derivatives decision is NOT made.** Re-opened to candidate (done through the new endpoint). Their curation status stays `quote_only`. Passages of any source that is `permission` or `quote_only` are excluded from retrieval by the `retrievable_passages` view, even if someone approves them. **Retrieval code must read only that view, never the `passages` table.** Wait for Aidan.
3. **Put Reading First, NSW review, REL PLC guide:** stay candidates, note "team intends to include; awaiting Aidan's license sign-off."
4. **URLs:** comprehension guide https://ies.ed.gov/ncee/wwc/practiceguide/14, English learners guide https://ies.ed.gov/ncee/wwc/practiceguide/19 (added to the YAML and the database).
5. **Evidence label rule (closes open question 12).**
   - WWC practice guides: store the guide's own rating (Strong / Moderate / Minimal) on the passages of each recommendation; Strong -> "Very sure", Moderate -> "Fairly sure", Minimal -> "Not sure yet".
   - Other government guides (England, Australia, NSW, Put Reading First, REL tools) support an answer but never raise the label alone, because they mostly summarize the same research. They carry `evidence_role = summary`.
   - Count independent evidence, not documents or passages: one source counts once.
   - Implemented in `api/app/evidence.py` (tested). Rating extraction is in `ingest/sor_ingest/ratings.py`; it runs for WWC practice guides and warns when it finds no ratings.
   - **My additions (please confirm):** unrated primary evidence follows the old CLAUDE.md idea: 2+ independent reviews (meta-analysis or National Reading Panel) -> Very sure; 1 review or 1 study -> Fairly sure. An unrated passage from a WWC guide does not raise the label. Overlap between a meta-analysis and the NRP is not detected.
6. In local dev (`AUTH_MODE=dev`) the audit actor is `dev-admin`. Real names appear once Cognito is on.

## 2026-11-19 — Open question 13 closed: unrated evidence rules (Viktoriia)
- 2+ independent reviews or meta-analyses that agree -> **Very sure**. 1 review or meta-analysis -> **Fairly sure**.
- 1 single study -> **Not sure yet**, unless large and controlled (randomized, OR >= 1,000 students with a comparison group) -> **Fairly sure**.
- Studies that disagree -> cap at **Not sure yet** and the answer says the research is mixed (`EvidenceResult.mixed`).
- Unrated WWC passages do not raise the label (confirmed).
- Overlap detection: accepted limitation for the PoC. The National Reading Panel and any meta-analysis published before 2001 count once together. Documented in ADR 0003.
- Implemented in `api/app/evidence.py`. Study design (randomized, sample size, comparison group) is entered in the admin approval form (migration 0004).
- **My interpretations (flag if wrong):** (a) the "disagree" cap applies to the whole label, even over a WWC Strong rating; (b) two or more agreeing small studies still stay at Not sure yet, because the rule only lifts a single large controlled study; (c) who decides that a passage "contradicts" the answer is Phase 2 (the claim-support verifier supplies it).

## 2026-11-19 — Push and accessibility (Viktoriia)
- Push `viktoriia/foundation` to GitHub (no merge to main): nothing should exist only on the laptop.
- The admin page counts for accessibility: Playwright + axe (WCAG 2.0/2.1 A and AA) run on the status tabs, review form, Re-open panel and error state; plus checks for 48px targets and a visible focus ring. `make e2e`, and a CI job.

## 2026-11-19 — Verified ratings, page labels, chunking fixes (Viktoriia)
- **src_0011 ratings verified** by Viktoriia against the official WWC page: Rec 1 Minimal, Rec 2 Strong, Rec 3 Strong, Rec 4 Moderate. Recorded with `sor-ingest verify-ratings` (sources.ratings_verified_*, logged in source_audit).
- **Ratings are usable only for a verified source.** `retrievable_passages` returns `evidence_rating` only when the source's ratings are verified. Re-processing with changed ratings withdraws the verification. Ratings on src_0120, src_0125, src_0126 are extracted but NOT verified, so they are hidden.
- **Page numbers:** `page` = PDF page, `page_label` = printed label (PyMuPDF `get_label()`), falling back to the PDF page. Teachers see labels.
- Dropped by the parser: running headers/footers, page numbers, tables of contents, reference lists, author bios, acknowledgements, disclosures, glossaries (all sources, not only src_0123), single-letter headings, the "Overview of Recommendations" table.
- Chunking: target 300-500 words, hard max 600, passages under 150 words merged into a neighbour unless that would cross a recommendation, rating or grade. Section heading is the first line of each passage.
- **My choices (flag if wrong):** (a) the glossary skip is global, so src_0125's glossary (3 pages) is skipped too; (b) the src_0120 checklist stays as 5 short passages, one per recommendation, because merging neighbours would mix their ratings; (c) src_0120 rates Recs 4-5 as "Low", which is outside Strong/Moderate/Minimal, so those are left unrated until Viktoriia decides.

## 2026-11-20 — Low = Minimal, glossary skip, journal front matter (Viktoriia)
- **"Low" is stored as Minimal** ("Not sure yet"). Older WWC guides (2009 RTI guide) used Strong/Moderate/Low; Low is the same bottom tier. Recorded in ADR 0003.
- **Glossary skip stays global** (also skips the src_0125 glossary).
- **Journal front matter is filtered** on the first two pages: article history (Received/Accepted/Published), licence and copyright lines, DOI lines, author lists and affiliations, "A R T I C L E I N F O". Titles, keywords and abstracts are kept.
- After "Low" was recognised, src_0120 Rec 2 changed from Moderate to Minimal. Ratings for src_0120, src_0125, src_0126 are extracted but unverified (hidden from retrieval) until Viktoriia checks them against the guides.

## 2026-11-20 — More ratings verified; src_0125 Rec 5 extraction fix (Viktoriia)
- **src_0120 (all 5) and src_0126 (all 4) ratings verified** against the official WWC pages.
- **src_0125 Rec 5 was extracted as Minimal; the WWC page says Moderate.** Cause: in the appendix each recommendation's title line comes first and its "Level of evidence" heading after it, so Rec 5's title line sat under Rec 4's leftover "Minimal Evidence" heading and the extractor took that. Fixed in code (a recommendation-start line does not take a rating from a heading that already has other text under it); no hand edit. src_0125 stays unverified until Viktoriia has seen the 5 re-extracted lines.

## 2026-11-20 — src_0125 verified; Bedrock access findings
- **src_0125 ratings verified** (Rec 1 Strong, Rec 2 Moderate, Rec 3 Minimal, Rec 4 Minimal, Rec 5 Moderate). All four WWC practice guides with ratings (src_0011, src_0120, src_0125, src_0126) are now verified; 146 passages carry a usable rating.
- **SSO profile `sor-dev` works** (account USM-SOR-ADA-32, role msaih_IsbUsersPS).
- **The Hub's service control policy explicitly denies `bedrock:ListInferenceProfiles` and `bedrock:ListFoundationModels`.** We cannot list enabled models; do not try to work around it. Model IDs come from AWS documentation and are confirmed only by a real call (needs Viktoriia's OK first).
- Documented IDs (not yet confirmed in the account): Haiku `us.anthropic.claude-haiku-5-5`; Sonnet `us.anthropic.claude-sonnet-5` (documented as "Claude Sonnet 5"); Titan embeddings `amazon.titan-embed-text-v2:0` (1024 dims). All go in config, never hard-coded.
- **Pending Viktoriia's OK:** 3 tiny test calls (1 each to Haiku, Sonnet, Titan; well under 1 cent) to confirm the IDs, plus a config file holding them. No embeddings or evals run until she has seen a cost estimate and approved it. Titan V2 price and region support were not in the searchable docs: check the Bedrock pricing page for the estimate.

## 2026-11-20 — Model test calls all denied (Viktoriia approved the calls)
- Added `config/models.yaml` (fast Haiku, large Sonnet, Titan V2, 1024 dims; env overrides).
- 1 tiny call each: **all three returned AccessDeniedException (403)**. Haiku: explicit deny in an SCP ((id withheld)). Sonnet and Titan: explicit deny in the permissions boundary `StorefrontModelBoundary`. No alternatives tried. Waiting on the Hub. Pricing/cost estimate not done (stopped per instruction).

## 2026-11-20 — Model policy, Sonnet 4.5 denied, local embeddings (Viktoriia)
- **Source of truth for allowed models: the Hub's IAM permissions boundary `StorefrontModelBoundary`**, as read by Viktoriia in IAM > Policies. It allows only `anthropic.claude-haiku-5-5` and `anthropic.claude-sonnet-4-5-20250929-v1:0` (inference profiles and foundation models, any region). No Titan or other embedding model.
- **Test call, `us.anthropic.claude-sonnet-4-5-20250929-v1:0`, us-east-2: AccessDeniedException**, explicit deny in the org SCP (id withheld) (the same SCP that blocks Haiku 5.5). So both allowed models are blocked by the SCP. Other regions not probed (Viktoriia asks the Hub). Logged as OPEN_QUESTIONS 15.
- **Config** (`config/models.yaml`): generation and claim check = Sonnet 4.5 for now; Haiku 5.5 recorded as `intended_fast`, not used until the SCP is resolved.
- **Embeddings: local BAAI/bge-small-en-v1.5, 384 dims** (ADR 0004, migration 0008). `embedder.py` reads the config; Titan code and default removed. All 1,619 passages embedded locally (`sor-ingest embed`). This departs from the CLAUDE.md stack table (Titan V2, 1024); CLAUDE.md should be updated by Viktoriia.
- **My choices (flag if wrong):** added a `sor-ingest embed` command that fills missing embeddings from stored text instead of re-running `process --all`, so verified ratings are not touched; chose `fastembed` (ONNX) over sentence-transformers/PyTorch to keep the container small.
- **Not built yet:** the Q&A engine. With every Claude call denied it cannot be tested live, so I stopped for Viktoriia's decision (build against fakes now, or wait for the Hub).

## 2026-11-20 — Q&A engine built against fakes (Viktoriia: "yes, build it; no evals, no live calls until I approve")
- **CLAUDE.md updated** (local only, gitignored): embeddings = local BAAI/bge-small-en-v1.5 (384 dims), models from `config/models.yaml`, ADR 0004; LLM row now names the two boundary-allowed models and the SCP block.
- Engine, verifier, router, Presidio redaction, hybrid retrieval, rate limit, kill switch, `query_log`, eval harness and `make eval` are built and unit-tested (87 tests) with fake model clients. **No live model call was made.** See ADR 0005.
- **My choices (flag if wrong):** `QA_ENABLED` defaults to off; model and verifier return structured output through a forced Converse tool; a quote needs >= 3 words and matches exactly except whitespace/typographic quotes; fewer than half of claims verified -> honest fallback; the myth correction is shown only if the myth has linked passages; threshold 0.70 (calibrated on 16 free local queries); no streaming; `make eval` runs the free retrieval-only mode.
- **Retrieval-only eval, first result:** 7 of 9 no-research/out-of-scope questions are caught before any model call (all 4 out-of-scope; fractions and photosynthesis still retrieve passages). All 18 real questions find passages.
- **Cost estimate (Sonnet 4.5, $3/$15 per M tokens, unconfirmed on AWS's own page):** about $0.03 per answered question, about $1.15 per 30-question eval run including the baseline.

## 2026-11-20 (overnight) — Commit the team docs (Viktoriia)
- Reverses the Phase 0 decision #4: `CLAUDE.md`, `docs/PLAN.md`, `docs/DECISIONS.md` and `design/wireframes/` are now committed. `docs/AWS_SETUP_SAFELY.md`, `docs/reference/` and `.claude/` stay ignored. `sor-frontend/` (the frontend session's worktree) is ignored.
- Scan before committing: gitleaks found nothing in any of them; the wireframes' embedded assets were decoded and had no emails, phone numbers or keys.
- **Removed:** the Hub's AWS organization ID and the SCP policy ID (in DECISIONS.md, OPEN_QUESTIONS.md and config/models.yaml), because the repo is public. They now read "id withheld". Because the two unpushed model/embedding commits contained them, those two local commits were rewritten before the first push (history is otherwise unchanged). Kept: the permissions-boundary policy name `StorefrontModelBoundary` (needed to talk to the Hub), team first names (Aidan, Kritika), and `sor-dev` / role names.

## 2026-11-20 (overnight) — Team questions in the eval set; router and threshold change
- `ingest/scripts/pdf_to_md.py` converts each PDF in `docs/reference/` to `.md` next to it (`docs/reference/` stays gitignored). The license checklist PDF yields almost no text (a form); the other three convert fine.
- Added the team's teacher-facing questions with `source: team` (t01-t06): Viktoriia's five from CSC 414 plus "What words should come first?" from the meeting notes. Left out Abdullah's five (student-facing, e.g. "Can you point to the letter...") and the two lesson-plan questions (OPEN_QUESTIONS 20).
- **Finding:** two team questions (digraphs sh/ch; "look at the picture") scored 0.65-0.68 and were wrongly treated as "no research" at the 0.70 threshold, while off-topic questions score up to 0.75. **Change (mine, flag if wrong):** `min_similarity` 0.70 -> 0.62, plus a router rule: a question with no reading/literacy vocabulary at all (fractions, photosynthesis, sourdough) is answered "no research" with no retrieval and no model call. Tests cover both lists. Retrieval-only eval now passes all three of its checks.
- `myth_id` in questions may be a list (any one counts): the team's picture question matches two myths' cues.

## 2026-11-20 (overnight) — Decodability checker (Phase 4, item 1)
- Built in plain code, no AI: `api/app/decodable/` = CMU Pronouncing Dictionary (`cmudict` package, ARPAbet) + a grapheme-phoneme table + backtracking alignment of spelling to pronunciation using only the taught graphemes. Per word: `decodable | heart_word | not_decodable | unknown`, a plain-language reason, the graphemes, and (for failures) the untaught graphemes it needs. `decodable` is true only for status `decodable`; a heart word is allowed but never labelled decodable; unknown words (not in the dictionary, or with a symbol) are never allowed.
- Inputs: taught graphemes by name (`sh`, `a_e`, `ee`...), an explicit heart-word list, and optionally the `grapheme_scope` order (`taught_through(scope, n)`). Seeds are drafts (OPEN_QUESTIONS 21).
- **My choices (flag if wrong):** soft c/g not taught by default; doubled consonants count as the single consonant; final "s" /z/ for words of 3+ letters; a split digraph needs a final "e" and only consonant graphemes in between; the failure explanation searches the full table for the cheapest alignment and lists the untaught graphemes it uses.
- 45 unit tests (digraphs sh/ch/th/ck/ng/nk/wh, silent e, blends, doubles, plurals, x/qu, vowel teams, r-controlled, heart words, unknown words, inputs, seeds). Spot check: 57 of 59 common K-1 words pass with a typical taught set; "bunny" and "happy" fail (final y).
