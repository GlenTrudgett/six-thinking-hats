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
Exit codes: 0 ok, 1 internal error, 2 input error, 3 configuration error, 4 degraded run.
Copy `.env.example` to `.env` for configuration. Never commit secrets.
