# Changelog
All notable changes follow [Keep a Changelog](https://keepachangelog.com) and SemVer.

## [Unreleased]
### Added
- Phase 1 foundation: settings, logging, schemas, ModelFactory, structured output, White Hat.
- Phase 2: prompts for all five hats plus Blue-Open and Blue-Close (versioned), parallel LangGraph
  workflow (intake, blue_open, five hats in parallel, blue_close), report rendering (Markdown and JSON),
  output sanitising, and the `sixhats run` command (text, file or stdin input; output file).
- Graph tests proving fan-in and a single `blue_close` execution.

### Changed
- Schemas aligned to the specification (Framing, HatOutput, FailureRecord, FinalReport).
- The CLI `run` command now runs the full workflow instead of a single hat.

### Fixed
- Logging no longer fails when `sys.stderr` is replaced or closed after configuration.
- CodeQL `init` and `analyze` steps now use the same major version; gitleaks ignores fake test keys.
