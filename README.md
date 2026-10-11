# Six Thinking Hats

Edward de Bono's *Six Thinking Hats* (ISBN 0-14-029666-2) as a LangGraph multi-agent application.
An administrator frames the request, runs the six hats, and collates a final report.
LLM-agnostic via LangChain (Anthropic and local OpenAI-compatible servers supported).

**Status:** Phase 1 (foundation). See `docs/` and CHANGELOG.md.

## Develop
```
uv sync
uv run pytest
uv run ruff check . && uv run mypy src && uv run bandit -r src
uv run sixhats hats
```
Copy `.env.example` to `.env` for configuration. Never commit secrets.
