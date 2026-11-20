.PHONY: dev test eval lint migrate seed

dev:
	docker compose up --build

test:
	cd api && uv run pytest
	cd ingest && uv run pytest -q
	cd web && npm test --if-present

eval:
	@echo "No eval set yet (Phase 2)."

lint:
	cd api && uv run ruff check . && uv run ruff format --check . && uv run mypy app tests
	cd ingest && uv run ruff check . && uv run ruff format --check . && uv run mypy sor_ingest tests
	cd web && npm run lint && npm run typecheck && npm run format:check

# Needs the database: docker compose up -d db
migrate:
	cd api && uv run alembic upgrade head

seed:
	cd api && uv run python -m app.seed myths
