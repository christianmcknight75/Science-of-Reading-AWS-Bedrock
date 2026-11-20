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
| 17 | `evals/questions.yaml` has 38 questions: 6 from the team (`source: team`) and 32 drafted by Claude. None is SME-reviewed. Needs an SME pass (especially `allowed_labels`). | SME / Viktoriia | Open |
| 18 | `min_similarity` is 0.62 (calibrated on 38 questions) and a router rule sends questions with no reading vocabulary to "no research". The live eval must show the model and verifier handle the rest. Re-tune after the first live run. | Claude / Viktoriia | Open |
| 19 | Myths in `api/seed/myths.json` have no `passage_ids`, so "Watch out for" never shows yet. Needs SME-approved links to corpus passages (and the SME review in #5). | SME | Open |
| 20 | The meeting notes (2026-10-13) list two sponsor questions that are lesson-plan features, not Q&A: "Is this lesson plan research-backed?" and "Am I following best practice?". Not in the eval set. The second sounds like rating the teacher, which CLAUDE.md rule 3 forbids; the notes frame it as a supportive, honest partner. Should the lesson-plan check answer it as "here is what the research says about each part", never a score? | Viktoriia / sponsor | Open |
| 21 | Decodability checker (`api/app/decodable/`): the draft phonics scope and sequence (`api/seed/grapheme_scope.json`, 50 graphemes in a typical K-2 order) and the draft heart-word list (`api/seed/heart_words.json`) were written by Claude and need an SME. Rules to confirm: "c" and "g" are hard only; doubled consonants count as the single consonant; final "s" may say /z/ (dogs, his, but not "is"); the vowel sound of final "y" (happy, bunny), soft c/g (rice, cage) and two-syllable words are not supported yet, so those words come back "not decodable". | SME (Kritika?) | Open |
| 22 | `api/app/stuck.py` has 7 draft mistake patterns (dropped ending, added sounds, sound order, vowel sound, digraph, beginning sound, first-letter guess) written by Claude. The project brief says to use Kritika's error list; it is not in the repo. Please send it and I will replace the rules. | Viktoriia / Kritika | Open |
| 23 | `api/seed/training_topics.json` (6 PD topics) is a Claude draft. Which PD topics will teachers actually be trained on in Mississippi? | SME / MDE | Open |
