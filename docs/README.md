# Documentation index

All documentation for **pipefy-agent-bridge** lives in this directory.

## Read in this order

| # | Document | Status | Purpose |
|---|----------|--------|---------|
| 1 | [../README.md](../README.md) | Active | Project overview and quick start |
| 2 | [TRY_IT_YOURSELF.md](TRY_IT_YOURSELF.md) | Active | Hands-on tour: **Pipefy** CLI → **Cursor SDK** → **NVIDIA NAT** |
| 3 | [LEARNINGS.md](LEARNINGS.md) | Active | Operational learnings (Pipefy truncation, Cursor/NAT limits, Encore) |
| 4 | [ARCHITECTURE_AND_IMPLEMENTATION_PLAN.md](ARCHITECTURE_AND_IMPLEMENTATION_PLAN.md) | Active | Architecture, justified decisions, and delivery phases |
| 5 | [BENCHMARKS.md](BENCHMARKS.md) | Active | Reliability & latency numbers (operator-reproducible) |
| 6 | [CLOUD.md](CLOUD.md) | Active | Cursor Cloud agent setup and run |
| 7 | [OPEN_DECISIONS.md](OPEN_DECISIONS.md) | Active | Resolved and open decisions |

## Supporting files (repository root)

| File | Purpose |
|------|-------------|
| [../.env.example](../.env.example) | Environment variable template |
| [../.gitignore](../.gitignore) | Ignores secrets, build artifacts, live eval fixtures |

## Shipped layout

| Path | Description |
|------|-------------|
| `../Makefile` | `doctor`, `tour`, `demo-cursor`, `demo-nat`, `demo-cloud`, `eval`, `profile-nat`, `similar`, `install-*` |
| `../configs/pipefy_nat_workflow.yml` | NAT `react_agent` + NIM + MCP (inventory-focused tool subset) |
| `../configs/tool_allowlist.yml` | Full curated MCP tool list @ pinned toolkit tag |
| `../demos/01_cursor_pipefy_ops.py` | Cursor SDK harness (local) |
| `../demos/03_cursor_cloud_ops.py` | Cursor SDK harness (cloud VM) |
| `../demos/02_nat_smoke.sh` | NAT smoke wrapper + failure detection |
| `../demos/prompts/*.txt` | Scenario prompts |
| `../eval/ground_truth.sh` | CLI JSON baselines → `fixtures/live/` |
| `../eval/compare.py` | Encore fact check (truncation-aware) |
| `../eval/run_eval.py` | Golden eval runner (`make eval`) |
| `../scripts/tour.sh` | Three-act tour + Encore |
| `../scripts/extract_nat_answer.py` | Parse `Workflow Result` from NAT logs |
| `../embeddings/` | Semantic card search (`make similar`) |

## Cross-reference map

```
README.md ──────────────► TRY_IT_YOURSELF.md (primary runbook)
        ├──────────────► LEARNINGS.md (operational limits)
        ├──────────────► BENCHMARKS.md (measured reliability)
        ├──────────────► CLOUD.md (optional cloud path)
        └──────────────► ARCHITECTURE_AND_IMPLEMENTATION_PLAN.md

TRY_IT_YOURSELF.md ─────► ARCHITECTURE §15 (scenarios)
        └──────────────► .env.example

ARCHITECTURE plan ──────► TRY_IT_YOURSELF.md (operator experience §16)
        ├──────────────► BENCHMARKS.md (eval strategy §17)
        └──────────────► OPEN_DECISIONS.md

OPEN_DECISIONS.md ──────► ARCHITECTURE §13 (layout), §14 (phases)
```

## External references

| Ecosystem | Canonical link |
|-----------|----------------|
| Pipefy toolkit (official) | https://github.com/pipefy/ai-toolkit |
| Cursor SDK | https://cursor.com/docs/sdk/python |
| NVIDIA NeMo Agent Toolkit (source) | https://github.com/NVIDIA/NeMo-Agent-Toolkit |
| NVIDIA NeMo Agent Toolkit (docs) | https://docs.nvidia.com/nemo/agent-toolkit/latest/index.html |
