# Changelog
All notable changes follow [Keep a Changelog](https://keepachangelog.com) and SemVer.

## [Unreleased]

### Added
- Quality checks, layer 1 (offline, run on every PR): prompt contract tests that cover every prompt file
  automatically (own hat, version, length limit, "data not instructions", preset list reaches Blue-Open);
  property-based report checks with Hypothesis (sequence length, one call per step, one summary per hat,
  `degraded` exactly when something failed, failed hats never reported as covered, Blue-Open fallback);
  and golden JSON-schema snapshots in `tests/golden/schemas.json`. Intentional schema changes are
  regenerated with `UPDATE_GOLDEN=1 uv run pytest tests/unit/test_golden_schema.py --no-cov`.
  New dev dependency: `hypothesis`.
- Blue checkpoints: `blue` is now a valid step inside your own order (`run --sequence white,green,blue,black`,
  the API, and a "+ blue checkpoint" button in the web interface). Blue summarises progress, lists gaps and
  gives the next hat a focus line. It cannot change the sequence. Rules in code: not first, not last, not
  adjacent to another Blue, counts toward the 8-step cap. A failed checkpoint is recorded and skipped.
  Reports gain `checkpoints` and a "Blue checkpoints" section. New prompt `blue_checkpoint` v1.

### Changed
- Blue-Close prompt is v3: it may use the checkpoint notes to describe how the thinking progressed.

## [1.1.0] - 2026-10-13
Presets, forced parallel mode, progress and cost reporting, and a web interface.

### Added
- Preset hat sequences: seven named orders (initial ideas, choosing between alternatives, identifying
  solutions, quick feedback, process improvement, problem solving, performance review). Blue-Open can choose
  one (its order then comes from code, not the model) or you can: `sixhats presets`, `run --preset ID`,
  `run --sequence white,green,black` (1 to 8 steps, hats may repeat). The report names the preset. The
  orders come from a secondary source, not the book text, and are labelled "advanced". Blue-Open prompt is v3.
- `run --mode parallel` forces all five hats at once, ignoring presets (cannot be combined with
  `--preset` or `--sequence`).
- Progress and cost: progress lines on stderr (`--quiet` hides them), elapsed time and token counts, and an
  optional cost estimate from your own prices. The estimate always carries its currency
  (`est. cost: USD $0.0123`); `SIXHATS_RUN__PRICE_CURRENCY` is required with the two price settings and a
  partial set is a configuration error. Reports gain `elapsed_seconds`, `estimated_cost`, `cost_currency`.
  `.env.example` lists current model prices (USD) as comments.
- Web interface: `sixhats serve` (FastAPI, optional `web` extra, loopback by default, streams progress as
  server-sent events) and a Next.js/React front end in `web/` with presets, a custom hat order, live progress,
  Copy and Download as Markdown, and a "Start over" button. Styled with the palette of the book cover
  (`web/PALETTE.md`); no cover artwork or logo is used.
- Makefile for local work without Docker (`make check`, `test-fast`, `demo`, `web`, `dev`, live tests).
- Offline `demo` provider: runs the whole workflow with no key, network or cost, for trying the app and UI.
- Plans (docs only): Blue steps in the middle of a sequence, and quality checks.

### Fixed
- Web UI: a run longer than 30 seconds failed with "Error in input stream" because Next.js's rewrite proxy
  cut the stream. The proxy timeout is now 15 minutes, the API sends a keep-alive comment every 10 seconds
  during quiet steps, and a lost connection now gives a clear message.

## [1.0.0] - 2026-10-12
First stable release. Verified live on Claude (claude-sonnet-5-5) and a local llama.cpp server, and in the
container.

### Added
- Sequential mode (phase 3): when Blue-Open chooses `mode: sequential`, the hats run one at a time in its
  sequence and each sees the earlier hats' output (as a delimited data block). A hat may repeat (up to
  8 steps); each step is kept (`white`, `white#2`). Hats left out of a sequence are not "missing".
  In an evaluation, code puts yellow before black (de Bono, Penguin ed., ch. 3). The report records
  `mode` and `sequence`.
- Resilience (phase 4a): every model node has a timeout and bounded retries of transient errors. A failed
  hat becomes a failure record and a degraded report, not a crash. Blue-Open failure falls back to a
  default framing; Blue-Close failure falls back to a report built in code. In sequential mode a failed
  step is skipped. The report lists `failures` (node, hat, error type, attempts, HTTP status only).
  Sequential context is capped. New settings: `SIXHATS_RUN__NODE_TIMEOUT_SECONDS`, `NODE_RETRIES`,
  `RETRY_BACKOFF_SECONDS`, `MAX_CONTEXT_CHARS`.
- `sixhats diagnose`: versions, settings and prompt versions with secrets hidden; `--ping` makes one small
  model call and shows the underlying error types if it fails.
- Exit code 5: no hat produced any output, so there is nothing to report on. Full set: 0 ok, 1 internal,
  2 input, 3 configuration, 4 degraded, 5 no model output.
- Minimal hardened container image (multi-stage, non-root, no secrets baked in), a container check in CI,
  a nightly workflow (full suite, pip-audit, image rebuild, optional live tests), Dependabot for the
  Dockerfile (Python bumps held until `pyproject.toml` moves).

### Changed
- `blue_open` prompt is v2 (sequence guidance and repeats).

### Fixed
- API keys are trimmed, a blank key counts as not set, and a key with inner whitespace is rejected.
  A trailing space in `.env` used with `docker --env-file` previously surfaced as a connection error.
- Settings errors never echo the offending value; `run` reports them as exit 3.

## [0.2.0] - 2026-10-12
### Added
- Phase 1 foundation: settings, logging, schemas, ModelFactory, structured output, White Hat.
- Phase 2: prompts for all five hats plus Blue-Open and Blue-Close (versioned), parallel LangGraph
  workflow (intake, blue_open, five hats in parallel, blue_close), report rendering (Markdown and JSON),
  output sanitising, and the `sixhats run` command (text, file or stdin input; output file).
- Graph tests proving fan-in and a single `blue_close` execution.

### Added (Phase 1 close-out)
- Structured output tries native schema support, then falls back to JSON mode with parse and validate;
  one bounded repair retry in total. Auth and connection errors are never swallowed.
- Loopback integration tests of the local-server path through the real OpenAI client.
- Opt-in live tests (`SIXHATS_LIVE=1`) for a configured real model.

### Changed
- Schemas aligned to the specification (Framing, HatOutput, FailureRecord, FinalReport).
- The CLI `run` command now runs the full workflow instead of a single hat.

### Fixed
- Live runs on claude-sonnet-5-5 and claude-fable-5: temperature is omitted for models with fixed sampling,
  ChatAnthropic uses json_schema structured output, configuration errors exit with code 3, over-long
  model lists are trimmed, and Blue-Close prompt is v2. Verified with the live tests.
- Logging no longer fails when `sys.stderr` is replaced or closed after configuration.
- CodeQL `init` and `analyze` steps now use the same major version; gitleaks ignores fake test keys.
