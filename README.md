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

## Knowledge layer (Phase 1)
```
docker compose up -d db && make migrate && make seed      # create tables, load myths
cd ingest && uv run sor-ingest search --topic "phonics instruction"   # candidates only
uv run sor-ingest curated --dry-run; uv run sor-ingest curated        # curated source list -> review queue
# review at http://localhost:5173/#/admin  (after make dev), then:
uv run sor-ingest process --embedder stub                             # approved sources only
```

## Layout
`web/` React app · `api/` FastAPI · `ingest/` source search and ingestion · `infra/` AWS CDK (Python, later) · `evals/` · `docs/`
