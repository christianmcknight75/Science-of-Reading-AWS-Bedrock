# ADR 0003: Status audit, retrieval view, and evidence label

Status: accepted (2026-11-19)

## Decision
- Every change to `sources.status` is logged in `source_audit` (who, when, from, to, reason). A database trigger enforces this: a status change without an actor and a reason is refused, so it cannot happen by hand in `psql` or by a script that forgot to log.
- Admins can re-open rejected or approved sources through the API; a reason is required.
- Retrieval reads only the `retrievable_passages` view: approved sources that are not waiting on a permission or no-derivatives decision.
- The evidence label is computed in code (`api/app/evidence.py`) from WWC recommendation ratings stored on passages; summary sources (government guides, Put Reading First) never raise it; independent sources are counted once.

## Why
Public Records Act and CLAUDE.md rule 4: the record of who admitted a source to the corpus, and why, must exist and be trustworthy. The label must not be guessed by a model.

## Evidence label rules (final, 2026-11-19)
- WWC practice guides: the guide's own rating per recommendation (Strong / Moderate / Minimal) maps to Very sure / Fairly sure / Not sure yet. Unrated WWC passages never raise the label.
- Government guides and summaries never raise the label alone.
- Unrated primary evidence: 2+ independent agreeing reviews/meta-analyses = Very sure; 1 review = Fairly sure; 1 study = Not sure yet unless randomized or >= 1,000 students with a comparison group (Fairly sure).
- Older WWC guides (2009-2010, e.g. the RTI guide) rate evidence Strong / Moderate / Low. Low is the same bottom tier as the later "Minimal", so it is stored as Minimal (Not sure yet).
- A WWC rating is shown to the answer engine only after a person has verified the extracted ratings against the official guide (`sor-ingest verify-ratings`, logged in `source_audit`). Re-processing with different ratings withdraws the verification.
- Disagreeing evidence caps the label at Not sure yet and the answer says the research is mixed.

## Known limitation: overlapping evidence (accepted for the PoC)
Two reviews often cite the same underlying studies, so "independent" is only approximated. The code treats the National Reading Panel and every meta-analysis published before 2001 as one body of evidence (counted once together). Any other overlap between reviews is not detected, so a label can be slightly too confident. A later version could record which primary studies each review includes and count distinct studies.
