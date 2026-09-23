# Roadmap

Planned features for SkillForge. These are **proposals**, not yet implemented —
each describes the problem, a suggested approach, and where it would plug into the
current code. Contributions welcome; open an issue to claim one.

Status legend: 🟡 Planned · 🟢 In progress · ✅ Done

---

## 🟡 1. Evaluation set — measure transform accuracy

**Problem.** Today we can *see* a transform's output and whether it passes
validation, but we can't answer "is this skill getting *more* or *less* accurate
as I tweak the prompt or swap models?" There's no ground truth to compare against.

**Proposed approach.** Reuse the [LangSmith](https://smith.langchain.com/) datasets
that tracing already writes to:

1. Store labeled pairs (`input.csv` → `expected_output.csv`) per skill under
   `evals/<skill_id>/`.
2. Push them to a LangSmith **dataset** (one example per pair).
3. Run each skill over the dataset with a custom evaluator that scores
   **per-column accuracy** (exact match) and **validation pass rate**, reusing
   `services/validator.py`.
4. Report a score table and diff so prompt/model changes can be compared
   objectively (A/B via the `skill_id` / `operation` metadata already attached to
   traces).

**Touch points.** New `services/evaluate.py`; a CLI entry (`python -m evaluate
<skill_id>`); optional `evals/` folder; reuses existing validator and LangSmith
client.

**Config.** `LANGSMITH_TRACING` / `LANGSMITH_API_KEY` (already exist).

**Why it matters.** This is the difference between "it looked right once" and a
regression-safe skill. It also unlocks data-driven model selection (compare 1.5B
vs 3B on the same eval set).

**Effort.** Medium.

---

## 🟡 2. RAG skill selection — suggest a skill from the uploaded file

**Problem.** The user must know which skill matches their file. As the skill
library grows, picking the right one by hand gets error-prone.

**Proposed approach.** Match the uploaded file's shape against each skill:

1. On skill save, embed a signature of the skill (its input columns + description)
   using the local embedding model already available in LM Studio
   (`text-embedding-nomic-embed-text-v1.5`).
2. On upload, embed the file's header row + a few sample rows.
3. Return the top-N skills by cosine similarity as **suggestions** (the user still
   confirms — no silent auto-run).

**Touch points.** New `services/skill_match.py`; extend `POST /api/process` flow
with a `GET /api/suggest-skill` endpoint; the Transform page highlights suggested
skills.

**Config.** `EMBEDDING_MODEL` (new, default `text-embedding-nomic-embed-text-v1.5`).

**Why it matters.** Turns SkillForge from "pick the skill yourself" into "here's
the skill that fits" — a real UX win once there are more than a handful of skills.

**Effort.** Medium.

---

## 🟡 3. Persistent job store — RAM → SQLite/Redis

**Problem.** The async job store (`jobs` dict in `app.py`) lives in memory. It is
lost on server restart, so a completed result can't be reconnected to after a
restart, and history of *job metadata* (status, attempts, validation) isn't
durable — only the output files on disk are.

**Proposed approach.** Put the job store behind a small interface and back it with
a durable store:

1. Define a `JobStorePort` (get / set / list / prune) — same ports-and-adapters
   style as the rest of the project.
2. Provide two adapters: the current in-memory one (default, zero-dependency) and
   a **SQLite** adapter (single file, no extra service) for persistence.
3. Optionally a **Redis** adapter for multi-process / horizontal scaling later.
4. Select via config; the app code is unchanged behind the port.

**Touch points.** New `port/job_store_port.py` + `adapters/job_store/{memory,sqlite}.py`;
`app.py` uses the port instead of the raw `jobs` dict.

**Config.** `JOB_STORE` (new, `memory` | `sqlite` | `redis`, default `memory`);
`JOB_STORE_URL` for redis.

**Why it matters.** Makes reconnect and job history survive restarts, and is the
prerequisite for running SkillForge as more than a single local process.

**Effort.** Small–Medium (SQLite adapter); Medium (Redis).

---

## Notes

- Every item keeps SkillForge's **local-first, optional-dependency** principle: a
  new capability must degrade gracefully when its dependency or config is absent,
  exactly like LangSmith/LangGraph do today.
- See [ARCHITECTURE.md](ARCHITECTURE.md) for the ports-and-adapters structure these
  proposals build on.
