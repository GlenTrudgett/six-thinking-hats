# Six Thinking Hats

Edward de Bono's *Six Thinking Hats* (ISBN 0-14-029666-2) as a LangGraph multi-agent application.
An administrator frames the request, runs the six hats, and collates a final report.
LLM-agnostic via LangChain (Anthropic and local OpenAI-compatible servers supported).

**Status:** 1.0.0. Parallel and sequential modes, resilience, diagnose and a hardened container. See CHANGELOG.md.

## Develop
```
uv sync
uv run pytest
uv run ruff check . && uv run mypy src && uv run bandit -r src
uv run sixhats hats
```

## Commands

| Command | What it does |
|---|---|
| `sixhats run QUESTION` | Run the workflow and print the report |
| `sixhats presets` | List the preset hat sequences |
| `sixhats hats` | List the hats, their roles and prompt versions |
| `sixhats diagnose [--ping]` | Show versions and settings (secrets hidden); `--ping` tests the model |
| `sixhats version` | Print the version |

### `sixhats run`
```
sixhats run "Should we adopt a four-day week?"
echo "my question" | sixhats run -          # keeps it out of shell history
sixhats run --file question.txt --format json -o report.json
```

| Option | Meaning |
|---|---|
| `QUESTION` | The question, or `-` to read standard input |
| `--file`, `-f PATH` | Read the question from a file (under 1 MB; not together with QUESTION) |
| `--format markdown\|json` | Report format (default markdown) |
| `--output`, `-o PATH` | Write the report to a file; add `--force` to overwrite |
| `--preset ID` | Use a preset hat sequence (see below) |
| `--sequence a,b,c` | Use your own order of hats |

Exit codes: 0 ok, 1 internal error, 2 input error, 3 configuration error, 4 degraded run, 5 no model output (nothing to report on).
Copy `.env.example` to `.env` for configuration. Never commit secrets.

### Preset sequences
```
sixhats presets
sixhats run "Which vendor should we pick?" --preset choosing_between_alternatives
sixhats run "..." --sequence white,green,black   # 1-8 steps; hats may repeat
```
Presets (Blue opens and closes every one):

| Id | Order |
|---|---|
| `initial_ideas` | white → green |
| `choosing_between_alternatives` | white → green → yellow → black → red |
| `identifying_solutions` | white → black → green |
| `quick_feedback` | black → green |
| `process_improvement` | white → white → yellow → black → green → red |
| `problem_solving` | white → green → red → yellow → black → green |
| `performance_review` | red → white → yellow → black → green → red |

How the order is decided: `--preset` or `--sequence` wins. Otherwise Blue-Open may choose a preset (its
order then comes from code, not the model) or propose its own order. A preset or sequence runs the hats
one at a time, each seeing what came before. `--preset` and `--sequence` cannot be combined, and
`--sequence` accepts only `white`, `red`, `green`, `yellow`, `black`. In an evaluation, yellow is placed
before black. The report names the preset used.

The preset orders come from a secondary source, **not the book text**, and are marked "advanced" in the
code and in reports.

## Troubleshooting
```
sixhats diagnose          # versions and settings, secrets hidden
sixhats diagnose --ping   # also makes one small call to the model
```
A run keeps going when one hat fails: the report is marked degraded (exit 4) and lists what failed.
Exit 5 means no hat produced anything. Timeouts and retries: `SIXHATS_RUN__NODE_TIMEOUT_SECONDS`
(default 120; raise it for a slow local model) and `SIXHATS_RUN__NODE_RETRIES`.

## Container
```
docker build -t sixhats .
docker run --rm --read-only --cap-drop ALL --security-opt no-new-privileges \
  -e SIXHATS_LLM__ANTHROPIC_API_KEY sixhats run "Should we adopt a four-day week?"
```
The image runs as a non-root user, has no build tools and holds no secrets; pass keys as environment
variables at run time. Inside a container `127.0.0.1` is the container itself, so for a llama.cpp server
on your computer use:
```
docker run --rm --read-only --cap-drop ALL --add-host=host.docker.internal:host-gateway \
  -e SIXHATS_LLM__PROVIDER=local -e SIXHATS_LLM__MODEL=<model-name> \
  -e SIXHATS_LLM__LOCAL__BASE_URL=http://host.docker.internal:8080/v1 \
  -e SIXHATS_LLM__LOCAL__ALLOW_NON_LOOPBACK=true sixhats run "..."
```
A nightly workflow rebuilds the image and runs the full suite and `pip-audit`. To also run the live tests
nightly, add an `ANTHROPIC_API_KEY` repository secret and set the repository variable
`SIXHATS_NIGHTLY_LIVE` to `true`.

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
