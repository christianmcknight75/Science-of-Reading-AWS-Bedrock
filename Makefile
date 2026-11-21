.PHONY: dev test eval lint migrate seed e2e

dev:
	docker compose up --build

test:
	cd api && uv run pytest
	cd ingest && uv run pytest -q
	cd web && npm test --if-present

# Free: router + retrieval checks, no model call. Full pipeline: add --mode fake (stand-in model) or
# --mode live --live (spends money; also needs SOR_ALLOW_LIVE_MODEL_CALLS=1, only after approval).
eval:
	cd api && uv run python ../evals/run.py --mode retrieval

lint:
	cd api && uv run ruff check . && uv run ruff format --check . && uv run mypy app tests ../evals
	cd ingest && uv run ruff check . && uv run ruff format --check . && uv run mypy sor_ingest tests
	cd web && npm run lint && npm run typecheck && npm run format:check

# Needs the database: docker compose up -d db
migrate:
	cd api && uv run alembic upgrade head

seed:
	cd api && uv run python -m app.seed myths

# Accessibility + admin page tests (API is mocked; first run: cd web && npx playwright install chromium)
e2e:
	cd web && npm run e2e
