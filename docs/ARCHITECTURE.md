# Architecture

SkillForge separates **what to transform** (declarative skill files) from **how
to move data** (Python I/O). The LLM is the "brain"; the code is the "hands".

## Core idea

- A **skill** is a Markdown file (`skills/*.md`) whose body becomes the LLM system
  prompt. It owns all transformation logic — mapping rules, business rules, output
  format.
- The **code** only handles common I/O: read the upload, call the LLM, split/save
  CSV, bundle ZIPs, validate, and serve downloads. It contains no per-skill logic.

Adding a new transformation means writing a skill file, not changing code.

## Ports & adapters (hexagonal)

Business logic depends on interfaces, not concrete implementations:

- `port/llm_port.py`, `port/storage_port.py`, `port/execution_port.py` define the
  contracts.
- `adapters/llm`, `adapters/storage`, `adapters/engine` provide implementations.
- `services/` holds logic that is unaware of HTTP or the specific LLM backend.

`services/self_correct.py` follows the same spirit: it receives `llm_call` and
`parse_sections` as injected callables, so it has no knowledge of FastAPI, OpenAI,
or skills — which makes it testable with a stub LLM.

## Transform request flow (async jobs)

Transforms can take minutes on a local model, so they run as background jobs:

```
POST /api/process ──▶ create job (status: processing) ──▶ return {job_id}
                              │
                              ▼  asyncio.create_task
                      _process_job(job_id, skill, file_content)
                              │
                    _run_transform() ── self-correction graph ──▶ result
                              │
                     jobs[job_id] = {status: done, result}

GET /api/jobs/{job_id} ──▶ status while processing, result when done
```

The browser stores `job_id` in `sessionStorage` and polls `/api/jobs/{job_id}`.
On reload or navigation it re-polls the same id, so a finished result (and its
download button) is restored — the work lives on the server, not the page.

## Self-correction graph

`services/self_correct.py` builds a [LangGraph](https://langchain-ai.github.io/langgraph/)
state machine:

```
START ──▶ generate ──▶ (passed?) ──▶ END
                          │
                       failed & attempts < max
                          ▼
                       correct ──▶ (passed?) ──▶ END
                          ▲___________│ (retry)
```

- `generate` calls the LLM and validates the output.
- `correct` feeds the validation errors back into the prompt and re-generates.
- `route` ends when validation passes or `SELF_CORRECT_MAX_ATTEMPTS` is reached.

If `langgraph` is not installed, `build_correction_runner` returns a plain-Python
loop with identical behavior.

## Observability

When `LANGSMITH_TRACING=true`, the OpenAI client is wrapped with `wrap_openai` and
the transform is wrapped with `@traceable`. Each call is traced with `skill_id`,
`job_id`, and `operation` metadata, and LangGraph nodes appear as nested spans —
so a trace shows `transform → LangGraph → generate/correct → ChatOpenAI`. All of
this is a no-op when tracing is disabled or the package is absent.

## Persistence

Two stores with different lifetimes:

- **Job store** (`jobs` dict, in RAM) — recent job status/results for reconnect.
  Bounded to `MAX_JOBS`; cleared on restart.
- **`outputs/` folder** (on disk) — the generated CSV/ZIP files. Permanent, and the
  source of the History page, so past results are downloadable even after a restart.

## Where to extend

| To change… | Edit… |
|---|---|
| A transformation's rules | a `skills/*.md` file (no code) |
| How output is split/saved | `_handle_single_output` / `_handle_multi_output` in `app.py` |
| Validation rules | `services/validator.py` |
| Retry/correction behavior | `services/self_correct.py` |
| The LLM backend | `adapters/llm` (any OpenAI-compatible server) |
