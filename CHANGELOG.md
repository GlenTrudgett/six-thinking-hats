# Changelog
All notable changes follow [Keep a Changelog](https://keepachangelog.com) and SemVer.

## [Unreleased]
### Fixed
- A stray space in the API key (easy to get from a Docker `--env-file`) no longer breaks the request header:
  keys are trimmed, a blank key counts as not set, and a key with inner whitespace is rejected.
- Settings errors never echo the offending value, so a bad key can't leak into an error message; `run`
  reports them as exit 3, the same as `diagnose`.
- `diagnose --ping` shows the underlying error types for a failed call.
### Added
- Phase 4c: minimal hardened container image (multi-stage, non-root, no secrets baked in), `.dockerignore`,
  a container build and security check in CI, a nightly workflow (full suite, pip-audit, image rebuild,
  optional live tests), and Dependabot for the Dockerfile.
### Added
- `sixhats diagnose`: versions, settings and prompt versions with secrets hidden (keys show only as set or
  not set); `--ping` makes one small model call and reports the result. Exit 3 for bad config, 5 if the ping fails.
### Added
- Phase 4a, resilience: every model node runs with a timeout and bounded retries of transient errors
  (timeouts, dropped connections, 408/429/5xx). A failed hat becomes a failure record and a degraded
  report, not a crash. Blue-Open failure falls back to a default framing (all five hats, parallel);
  Blue-Close failure falls back to a report built in code from the hats' own words. In sequential mode a
  failed step is skipped and later hats continue.
- The report lists `failures` (node, hat, error type, attempts, HTTP status only; never prompt or reply text).
- Sequential context is capped (`SIXHATS_RUN__MAX_CONTEXT_CHARS`, oldest steps dropped first).
- New settings: `SIXHATS_RUN__NODE_TIMEOUT_SECONDS`, `NODE_RETRIES`, `RETRY_BACKOFF_SECONDS`.
- Exit code 5: no hat produced any output, so there is nothing to report on.
- Configuration errors are never degraded: they stop the run (exit 3).
### Added
- Phase 3, sequential mode: when Blue-Open chooses `mode: sequential`, the hats run one at a time in its
  sequence and each sees the earlier hats' output (as a delimited data block). A hat may repeat
  (up to 8 steps); each step is kept (`white`, `white#2`). Hats left out of a sequence are not "missing".
- Deterministic sequence rule from de Bono (Penguin ed., ch. 3): in an evaluation, yellow goes before black.
- The report records `mode` and `sequence`; Markdown shows "Sequence: Blue → ... → Blue".

### Changed
- `blue_open` prompt is v2 (sequence guidance and repeats).

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
