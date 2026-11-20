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

## Layout
`web/` React app · `api/` FastAPI · `ingest/` source search and ingestion · `infra/` AWS CDK (Python, later) · `evals/` · `docs/`
