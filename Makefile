# Everyday commands for working on this project without Docker. Run `make` to see them.
.DEFAULT_GOAL := help
.PHONY: help setup check fix test test-fast demo ui api web dev live-claude live-local quality quality-judge quality-local quality-compare clean

help:  ## Show this list
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-12s %s\n", $$1, $$2}'

setup:  ## Install everything (Python + web extras, and the web UI's npm packages)
	uv sync --all-extras
	cd web && npm install --no-audit --no-fund

check:  ## All the checks CI runs: lint, format, types, security, tests with coverage
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy src
	uv run bandit -q -r src
	uv run pytest
	cd web && npm run lint

fix:  ## Auto-fix lint and formatting
	uv run ruff check --fix .
	uv run ruff format .

test:  ## Run the tests (offline, with coverage)
	uv run pytest

test-fast:  ## Run the tests without coverage; add K=name to pick tests, e.g. make test-fast K=preset
	uv run pytest --no-cov -q $(if $(K),-k $(K),)

demo:  ## Run a question with the offline demo model (no key, no cost): make demo Q="..." ARGS="--preset quick_feedback"
	SIXHATS_LLM__PROVIDER=demo uv run sixhats run "$(or $(Q),Should we adopt a four-day week?)" $(ARGS)

api:  ## Start the API on http://127.0.0.1:8000 with your .env settings
	uv run sixhats serve

ui:  ## Start the web UI on http://localhost:3000 (needs the API running)
	cd web && npm run dev

web:  ## API with the demo model plus the UI, together: try the whole app with no key (Ctrl-C stops both)
	@$(MAKE) -j2 api-demo ui

api-demo:
	SIXHATS_LLM__PROVIDER=demo uv run sixhats serve

dev:  ## API with your real model plus the UI, together (Ctrl-C stops both)
	@$(MAKE) -j2 api ui

live-claude:  ## Live tests against Claude (needs SIXHATS_LLM__ANTHROPIC_API_KEY in .env or your shell)
	SIXHATS_LIVE=1 SIXHATS_LLM__PROVIDER=anthropic uv run pytest tests/live -m live --no-cov -s

live-local:  ## Live tests against llama.cpp: make live-local MODEL=<name> [URL=http://127.0.0.1:8080/v1]
	SIXHATS_LIVE=1 SIXHATS_LLM__PROVIDER=local SIXHATS_LLM__MODEL=$(MODEL) \
	SIXHATS_LLM__LOCAL__BASE_URL=$(or $(URL),http://127.0.0.1:8080/v1) \
	uv run pytest tests/live -m live --no-cov -s

quality:  ## Behavioural checks on Claude, spends money: make quality [LIMIT=3] [BUDGET=1.50]
	SIXHATS_QUALITY=1 SIXHATS_LLM__PROVIDER=anthropic \
	$(if $(LIMIT),SIXHATS_QUALITY_LIMIT=$(LIMIT),) $(if $(BUDGET),SIXHATS_QUALITY_BUDGET=$(BUDGET),) \
	uv run pytest tests/quality -m quality --no-cov -s

quality-judge:  ## As 'quality', plus judge scores (one extra model call per question)
	SIXHATS_QUALITY=1 SIXHATS_QUALITY_JUDGE=1 SIXHATS_LLM__PROVIDER=anthropic \
	$(if $(LIMIT),SIXHATS_QUALITY_LIMIT=$(LIMIT),) $(if $(BUDGET),SIXHATS_QUALITY_BUDGET=$(BUDGET),) \
	uv run pytest tests/quality -m quality --no-cov -s

quality-local:  ## llama.cpp (free, slow): make quality-local MODEL=<name> [URL=...] [LIMIT=3] [NODE_TIMEOUT=300] [MAX_SECONDS=900]
	SIXHATS_QUALITY=1 SIXHATS_LLM__PROVIDER=local SIXHATS_LLM__MODEL=$(MODEL) \
	SIXHATS_RUN__NODE_TIMEOUT_SECONDS=$(or $(NODE_TIMEOUT),300) \
	SIXHATS_QUALITY_MAX_SECONDS=$(or $(MAX_SECONDS),900) \
	SIXHATS_LLM__LOCAL__BASE_URL=$(or $(URL),http://127.0.0.1:8080/v1) \
	$(if $(LIMIT),SIXHATS_QUALITY_LIMIT=$(LIMIT),) \
	uv run pytest tests/quality -m quality --no-cov -s

quality-compare:  ## Compare result files: make quality-compare FILES="quality-results/a.json quality-results/b.json"
	uv run python -m tests.quality.compare $(FILES)

clean:  ## Remove caches and build output
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage web/.next
