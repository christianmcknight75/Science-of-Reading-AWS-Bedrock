# ADR 0001: Repo layout and tooling

Status: accepted (2026-11-19)

## Decision
- Monorepo folders: `web/` (React+Vite+TS+Tailwind), `api/` (FastAPI), `ingest/`, `infra/` (AWS CDK in **Python**), `evals/`, `design/`, `docs/`.
- Python 3.12, managed with **uv** (one lockfile per package); web uses npm.
- Fonts (Lexend, Atkinson Hyperlegible; SIL OFL) are self-hosted through the `@fontsource` npm packages, so no request goes to Google at runtime.
- The earlier Terraform placeholder folders were empty and were removed; CLAUDE.md specifies CDK.
- Local dev is Docker Compose (Postgres + pgvector, API, web) before anything touches AWS.

## Why
One language (Python) across API, ingestion and infrastructure; one security boundary on AWS; simple handoff to MDE.
