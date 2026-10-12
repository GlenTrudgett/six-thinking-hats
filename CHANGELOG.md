# Changelog
All notable changes follow [Keep a Changelog](https://keepachangelog.com) and SemVer.

## [Unreleased]
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
