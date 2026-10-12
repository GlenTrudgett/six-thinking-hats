# Six Thinking Hats

Edward de Bono's *Six Thinking Hats* (ISBN 0-14-029666-2) as a LangGraph multi-agent application.
An administrator frames the request, runs the six hats, and collates a final report.
LLM-agnostic via LangChain (Anthropic and local OpenAI-compatible servers supported).

**Status:** Phase 2 (hats and parallel graph). Sequential mode, resilience, diagnose and the container are phases 3 and 4. See CHANGELOG.md.

## Develop
```
uv sync
uv run pytest
uv run ruff check . && uv run mypy src && uv run bandit -r src
uv run sixhats hats
```

## Use
```
sixhats run "Should we adopt a four-day week?"
echo "my question" | sixhats run -          # keeps it out of shell history
sixhats run --file question.txt --format json -o report.json
```
Exit codes: 0 ok, 1 internal error, 2 input error, 3 configuration error, 4 degraded run, 5 no model output (nothing to report on).
Copy `.env.example` to `.env` for configuration. Never commit secrets.

## Check against a real model (live tests)
The normal test suite runs offline with fake models. To check a real model, opt in explicitly:
```
# Local OpenAI-compatible server (llama.cpp, Ollama, ...)
SIXHATS_LIVE=1 SIXHATS_LLM__PROVIDER=local SIXHATS_LLM__MODEL=<model-name> \
SIXHATS_LLM__LOCAL__BASE_URL=http://127.0.0.1:8080/v1 \
uv run pytest tests/live -m live --no-cov -s

# Anthropic
SIXHATS_LIVE=1 SIXHATS_LLM__PROVIDER=anthropic SIXHATS_LLM__ANTHROPIC_API_KEY=<key> \
uv run pytest tests/live -m live --no-cov -s
```
Structured output tries the provider's native schema support first, then falls back to a JSON-mode
prompt with parsing and validation, so models without schema or tool support still work.
