# Changelog

All notable changes to SkillForge are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project aims to follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- **Async job processing** — `POST /api/process` now returns a `job_id` immediately
  and runs the transform in the background. Poll `GET /api/jobs/{job_id}` for status
  and result. The Transform page persists the job id in `sessionStorage` and
  reconnects on reload/navigation, so long transforms are no longer lost when you
  switch pages.
- **Self-correction loop** — when output fails validation, the errors are fed back
  to the LLM to fix automatically, implemented as a LangGraph state machine
  (`services/self_correct.py`). Configurable via `SELF_CORRECT_MAX_ATTEMPTS`
  (default `2`; `1` disables it). Falls back to plain Python when `langgraph`
  is not installed.
- **LangSmith observability** — optional tracing of every LLM call (prompt,
  response, latency, tokens) plus each self-correction step, with `skill_id`,
  `job_id`, and `operation` attached as metadata/tags. Enabled with
  `LANGSMITH_TRACING=true`; a no-op when disabled or uninstalled.
- **History page** (`/history`, `GET /api/history`) — lists past transforms read
  from the `outputs/` folder on disk, with per-file and ZIP downloads. Survives
  server restarts.
- **Input ⟷ Output compare** — toggle any result between the transformed output
  and the original source table.
- **Row-count selector** — choose 10 / 25 / 50 / All preview rows per table.
- **Auto-corrected badge** — the UI shows when the self-correction loop fixed a
  validation error and how many attempts it took.

### Changed
- `_csv_preview` now returns up to 200 rows (was 10) so the row-count selector has
  data to page through.
- HTML pages are served with `Cache-Control: no-cache` to avoid stale JavaScript.
- Default model reference updated to `qwen2.5-coder-3b-instruct`.
- `pandas` pinned to `2.2.3` (prebuilt wheels for Python 3.13).

### Fixed
- Validator crash (`'list' object has no attribute 'strip'`) when the model
  produced a row with more columns than the header — `csv.DictReader` collects
  the extras under a `None` key as a list. Empty-value checks now skip it.
- LLM responses whose `message.content` is a list of content blocks (returned by
  some OpenAI-compatible servers) are normalized to text before use.

## [0.1.0]

### Added
- Initial release: local LLM-powered CSV transformation via `skill.md` files,
  Skill Generator, multi-file output with `---SPLIT---`, validation engine,
  real-time SSE logs, and skill management.
