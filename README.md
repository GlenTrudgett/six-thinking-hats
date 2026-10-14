# Six Thinking Hats

Edward de Bono's *Six Thinking Hats* (ISBN 0-14-029666-2) as a LangGraph multi-agent application.
An administrator frames the request, runs the six hats, and collates a final report.
LLM-agnostic via LangChain (Anthropic and local OpenAI-compatible servers supported).

**Status:** version 1.1.0: parallel and sequential modes, presets, resilience, progress and cost reporting, a web interface and a container. See CHANGELOG.md.

## Develop (no Docker needed)
Run `make` to list the shortcuts:
```
make setup        # once: Python and web packages
make check        # everything CI runs
make test-fast K=preset   # quick tests, just the ones matching "preset"
make demo         # a full run with the offline demo model: no key, no cost
make web          # API (demo model) + web UI together: try the whole app with no key
make dev          # API (your real model from .env) + web UI together
make live-claude  # live tests on Claude;  make live-local MODEL=<name> for llama.cpp
```
The **demo model** (`SIXHATS_LLM__PROVIDER=demo`) needs no key or network and returns fixed text labelled
"[demo output, not from a model]". It exercises framing, presets, progress, tokens and the report, so you
can work on features and the UI without spending tokens. Never use it for real analysis.
Without `make`, the same things are plain commands, for example:
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
| `--quiet`, `-q` | Do not print progress lines to standard error |
| `--mode parallel` | Force all five hats to run at once, ignoring presets (default `auto`: Blue-Open decides) |

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
`--sequence` accepts `white`, `red`, `green`, `yellow`, `black` and `blue` (see below). In an evaluation, yellow is placed
before black. The report names the preset used.

The preset orders come from a secondary source, **not the book text**, and are marked "advanced" in the
code and in reports.

### Blue checkpoints
Put `blue` between hats in your own order and the Blue Hat pauses there:
```
sixhats run "Should we open a second site?" --sequence white,green,blue,black,yellow
```
At a checkpoint Blue reads what the hats have said so far and writes what has been covered (up to 3
points), what is still missing (up to 3) and a one-line focus for the **next hat**, which receives it as
data. The report gains a "Blue checkpoints" section and the final summary takes the checkpoints into
account. Rules, enforced in code: Blue cannot be the first or last step (Blue already opens and closes
every run), two Blues cannot be adjacent, and the 8-step cap counts Blue. A checkpoint cannot change the
order of the hats. If one fails it is recorded in the report (the run is then marked degraded) and the
next hat runs without it. Each checkpoint is an extra model call and counts toward the cost estimate.
No preset uses a checkpoint yet, and Blue-Open is not asked to add them; they are chosen by you (in the
web interface: "+ blue checkpoint" under "My own order").

### Progress and cost
While a run is going, each step prints to standard error (the report still goes to standard output, so
`> report.md` stays clean):
```
[   2.1s] intake: done
[   6.8s] blue_open: framed (sequential: white, green)
[  14.0s] sequential: done: white, green
[  19.5s] blue_close: done
usage: 5120 in / 1480 out tokens, 19.5s
```
Use `--quiet` to hide the progress lines. Tokens and time are always shown, and are in the report footer and
JSON (`token_usage`, `elapsed_seconds`). For a money estimate, set your own prices per million tokens in
`.env` (none are built in, because prices change), together with the **currency** they are written in:
```
SIXHATS_RUN__PRICE_INPUT_PER_MTOK=2.0
SIXHATS_RUN__PRICE_OUTPUT_PER_MTOK=10.0
SIXHATS_RUN__PRICE_CURRENCY=USD
```
Set all three or none (anything partial is a configuration error, exit 3). The estimate is always shown with
its currency, for example `est. cost: USD $0.0123`, and is in the report JSON as `estimated_cost` with
`cost_currency`. Anthropic lists prices in USD; the app does no currency conversion, so for AUD convert the two
prices yourself and set `PRICE_CURRENCY=AUD`. `.env.example` has a table of the current model prices.

## Web interface
A browser front end (Next.js and React) sits on a small local API.
```
uv sync --extra web                 # once: adds FastAPI and uvicorn
uv run sixhats serve                # API on http://127.0.0.1:8000
cd web && npm install && npm run dev   # UI on http://localhost:3000
```
Open http://localhost:3000, type a question, choose how the hats work (Blue decides, all five at once, a
preset, or your own order), and press Run. Progress appears live, then the report, with Copy and Download
as Markdown. The model key stays in the Python API's `.env`; the browser never sees it. The API listens on
127.0.0.1 only by default and has **no login**, so do not expose it to a network you do not trust
(`serve --host` warns if you do). The UI forwards `/api` to `http://127.0.0.1:8000`; set
`SIXHATS_API_URL` for the Next server to point elsewhere.

## Troubleshooting
If the web UI shows "Error in input stream" or "connection lost" part-way through a run, the API stopped or
the connection dropped: check the terminal running `sixhats serve` for errors and try again. (Runs over
30 seconds used to be cut by the Next.js proxy; that is fixed.)
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
