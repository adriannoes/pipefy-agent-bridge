# Product Requirements Documents (PRD) — index & roadmap

This directory holds the PRDs for **pipefy-agent-bridge**. PRDs are the bridge between the
planning docs and execution:

```
docs/ (architecture, runbook, decisions)
   └─► PRD (problem, scope, requirements, acceptance criteria)
          └─► tasks (engineering/tasks/, via /generate-tasks)
                 └─► sprints → build
```

Authoring conventions live in [.cursor/commands/prd.md](../../.cursor/commands/prd.md) and
[.cursor/commands/generate-tasks.md](../../.cursor/commands/generate-tasks.md).

## Roadmap

The initiative is split into **one MVP PRD + three stretch PRDs**, mapped 1:1 to the phases in
[docs/ARCHITECTURE_AND_IMPLEMENTATION_PLAN.md](../../docs/ARCHITECTURE_AND_IMPLEMENTATION_PLAN.md) §14.

| PRD | File | Status | Phase(s) | Scope summary |
|-----|------|--------|----------|---------------|
| **PRD-1 — Reproducible MVP Tour** | [prd-pipefy-agent-bridge-mvp.md](prd-pipefy-agent-bridge-mvp.md) | **Done** (2026-06-02) | 0–4 (shipped) | `doctor` → `demo-cursor` → `demo-nat` → `tour` for `inventory`, `eval/compare.py` fact check, lint-only CI, TRY_IT_YOURSELF Steps 0–4 |
| **PRD-2 — NAT Profiler & Evaluation** | [prd-2-nat-profiler-and-evaluation.md](prd-2-nat-profiler-and-evaluation.md) | **Done** (2026-06-03) | 5 | NAT profiler, `eval/golden.yaml`, `make eval` reliability runner, dated [`docs/BENCHMARKS.md`](../../docs/BENCHMARKS.md) |
| **PRD-3 — Cursor Cloud Agent** | _not written_ | Backlog | 6 | `CloudAgentOptions` + `repos` + MCP stdio in a Cursor-hosted VM |
| **PRD-4 — GPU Semantic Search** | _not written_ | Backlog | 7 | NIM embeddings + FAISS/cuVS "find similar cards", with CPU fallback |

**Status legend:** Draft for sign-off · Approved · In progress · Done · Backlog (not written yet).

### PRD-1 shipped — scope deltas (vs original draft)

| Area | Planned | As built |
|------|---------|----------|
| Upstream toolkit | Pin a tag | **`pipefy/ai-toolkit@v0.2.0-beta.2`** (`PIPEFY_TOOLKIT_REF` in Makefile) |
| MCP allowlist | 8–15 tools | **12** tools in `configs/tool_allowlist.yml` |
| NIM model | `8b` default, `70b` optional | **`meta/llama-3.1-8b-instruct`** in workflow YAML; `70b` swap documented, tier access not validated |
| Harness deps | Document installs | Pinned: **`cursor-sdk==0.1.6`**, **`nvidia-nat[langchain,mcp]==1.7.0`** |
| Eval gate | `inventory` only | Unchanged; `stale_cards` / `summary` runnable via `SCENARIO=` but **not** in `make tour` / `eval/compare.py` |
| Runbook | Steps 0–3 | **Steps 0–4** (Step 4 = `make tour` + encore fact check) |
| Git baseline | Initial commit | **Done** — initial local commit created (no remote push until complete & tested) |

Execution trace: [engineering/tasks/tasks-prd-pipefy-agent-bridge-mvp.md](../../engineering/tasks/tasks-prd-pipefy-agent-bridge-mvp.md) (tasks 1.0–5.0 complete).

### PRD-2 in progress — scope deltas (vs draft)

| Area | Planned | As built (so far) |
|------|---------|-------------------|
| Golden set | Multiple scenarios | **`inventory` only** in `eval/golden.yaml`; `stale_cards`/`summary` commented optional until example fixtures exist |
| Profiler | Enable on default `nat run` | **Opt-in** via `configs/pipefy_nat_workflow_profile.yml` + `make profile-nat`; default `make demo-nat` unchanged |
| Reliability runner | `make eval` | **Shipped** — first-attempt vs with-retries pass rate, median/p90 latency, `8b`/`70b` via `--model` |
| Benchmarks report | `docs/BENCHMARKS.md` | **Template shipped** (task 4.0); dated measured run + D18/D19 (task 5.3) pending operator |

Execution trace: [engineering/tasks/tasks-prd-2-nat-profiler-and-evaluation.md](../../engineering/tasks/tasks-prd-2-nat-profiler-and-evaluation.md) (tasks 1.0–3.0 complete; 4.0–5.4 open).

## Sequencing & dependencies

- **PRD-1 (MVP) is done.** Stretch PRDs (2–4) depend on this baseline and are written
  **just-in-time**, only when that phase is prioritized.
- **PRD-4 has an explicit gate:** do not start GPU semantic search until the MVP Cursor + NAT
  demos are green (architecture §12.4).
- PRD-2 and PRD-3 are independent of each other; either can follow the MVP.

## Out-of-PRD scope today

- `stale_cards` / `summary` scenarios are **best-effort** in PRD-1 (prompts created and runnable,
  not part of the acceptance gate). If they need formal delivery later, fold them into PRD-2 or a
  small PRD-1.1 — not required for the MVP.
- The write scenario (`move_card`) is gated and out of scope until explicitly prioritized.

## Decisions

Cross-cutting choices are tracked in
[docs/OPEN_DECISIONS.md](../../docs/OPEN_DECISIONS.md). D1–D14 are resolved; stretch decisions
(D15 Cloud, D16 GPU backend, D17 `nat mcp serve`) are resolved inside their respective stretch PRDs.
