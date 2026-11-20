.PHONY: dev test eval lint

dev:
	docker compose up --build

test:
	cd api && uv run pytest
	cd ingest/source_search && uv run --no-project --with pytest pytest tests -q
	cd web && npm test --if-present

eval:
	@echo "No eval set yet (Phase 2)."

lint:
	cd api && uv run ruff check . && uv run ruff format --check . && uv run mypy app
	cd web && npm run lint && npm run typecheck && npm run format:check
