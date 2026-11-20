# Reading Helper (SoR Assistant)

A research-grounded assistant that helps K–3 teachers turn science-of-reading training into classroom practice.
Built by Team ADA with the USM AI Innovation Hub for the Mississippi Department of Education. Proof of concept.

Advisory only. Teachers are the only users; no student data is stored.

## Run locally
```
make dev    # Postgres + API (http://localhost:8000/health) + web (http://localhost:5173)
make test
make lint
```

## Knowledge layer and engine (backend)
```
docker compose up -d db && make migrate && make seed                   # tables, myths
cd ingest
uv run sor-ingest curated --dry-run; uv run sor-ingest curated        # curated source list -> review queue
# review and approve at http://localhost:5173/#/admin (after make dev), then:
uv run sor-ingest process --embedder local                             # parse approved sources (downloads PDFs)
uv run sor-ingest embed --embedder local                               # local BGE embeddings, no AWS
cd ../api && uv run python -m app.myth_links load                      # draft myth links (never shown to teachers)
```

## API with the stand-in model (no AWS needed)
Bedrock is blocked for this account (`docs/OPEN_QUESTIONS.md` 15), so the API ships with a **fake model** for local use:
```
cd api && AUTH_MODE=local QA_ENABLED=true LLM_MODE=fake CORS_ORIGINS=http://localhost:5173 \
  uv run uvicorn app.main:app --port 8000
uv run python -m app.users create-admin --email you@example.org --name "You" --district "Local"   # first admin
```
Everything the fake model writes is labelled "[Fake model]". Endpoints: `docs/API_CONTRACT.md`. The Q&A kill switch
(`QA_ENABLED`) is off by default. Evals: `make eval` (free, no model call).

## Layout
`web/` React app · `api/` FastAPI · `ingest/` source search and ingestion · `infra/` AWS CDK (Python, later) · `evals/` · `docs/`
