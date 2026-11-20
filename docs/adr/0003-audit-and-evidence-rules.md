# ADR 0003: Status audit, retrieval view, and evidence label

Status: accepted (2026-11-19)

## Decision
- Every change to `sources.status` is logged in `source_audit` (who, when, from, to, reason). A database trigger enforces this: a status change without an actor and a reason is refused, so it cannot happen by hand in `psql` or by a script that forgot to log.
- Admins can re-open rejected or approved sources through the API; a reason is required.
- Retrieval reads only the `retrievable_passages` view: approved sources that are not waiting on a permission or no-derivatives decision.
- The evidence label is computed in code (`api/app/evidence.py`) from WWC recommendation ratings stored on passages; summary sources (government guides, Put Reading First) never raise it; independent sources are counted once.

## Why
Public Records Act and CLAUDE.md rule 4: the record of who admitted a source to the corpus, and why, must exist and be trustworthy. The label must not be guessed by a model.
