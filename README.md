# Pipefy Agent Bridge Demo

**One MCP tool contract for Pipefy, two production-style agent harnesses.**

A reference implementation that connects **Pipefy** operations to AI agents through a single **Model Context Protocol (MCP)** tool layer, then orchestrates that layer with both the **Cursor SDK** and the **NVIDIA NeMo Agent Toolkit (NAT)** + **NIM** — proving MCP is the portability layer between ecosystems.

> **Disclaimer:** Community-maintained reference software. Not an official Pipefy, Cursor or NVIDIA product.

**Status:** Reference implementation — all four phases shipped (local dual-harness tour, reliability eval, Cursor Cloud, GPU-optional semantic search). Pipefy access is delegated entirely to the official [`AI toolkit`](https://github.com/pipefy/ai-toolkit); this repo is orchestration + validation only and never reimplements the Pipefy API.

## What you can run

| Capability | Command | Notes |
|------------|---------|-------|
| **Preflight** | `make doctor` | After `make install-pipefy-tools`; checks env + read-only Pipefy ping (never prints secrets). |
| **Pipefy → Cursor → NVIDIA tour** | `make tour` | Acts 1–3 on the `inventory` scenario + an automated fact check (Encore). |
| **Cursor SDK agent** | `make demo-cursor [SCENARIO=…]` | Local Cursor agent over Pipefy MCP (guaranteed-green path). |
| **NVIDIA NAT + NIM agent** | `make demo-nat [SCENARIO=…]` | Same MCP tools under a declarative YAML workflow (best-effort, retried). |
| **Reliability eval** | `make eval` | First-attempt vs with-retries pass rate + latency → [`docs/BENCHMARKS.md`](docs/BENCHMARKS.md). |
| **NAT profiler** | `make profile-nat` | Timing/iteration capture for `nat run`. |
| **Cursor Cloud agent** | `make demo-cloud` | Same `inventory` in a Cursor-hosted VM ([`docs/CLOUD.md`](docs/CLOUD.md)). |
| **Semantic card search** | `make similar QUERY="…"` | NIM embeddings + FAISS (CPU default, GPU opt-in) "find similar cards". |

## Run this first (~10 min with API keys)

Copy-paste path for anyone cloning the repo — installs tooling, validates config, runs the full three-act demo plus automated fact check:

```bash
git clone https://github.com/YOUR_ORG/pipefy-agent-bridge.git
cd pipefy-agent-bridge
cp .env.example .env   # fill Pipefy + CURSOR_API_KEY + NVIDIA_API_KEY (see .env.example)

make install-pipefy-tools
make install-cursor-demo
make install-nat-demo
make doctor

make tour
```

**Success looks like:** `Tour complete — all fact checks passed.`

**Unit tests (no API calls):** `uv sync --extra dev --extra embeddings && uv run pytest tests/ -v`

Install order, env variable table, extra scenarios, and troubleshooting: **[docs/TRY_IT_YOURSELF.md](docs/TRY_IT_YOURSELF.md)** (~20–30 min for the full walkthrough).

## Quick start

**Prerequisites:** macOS or Linux (WSL2 OK), Python 3.11+, [`uv`](https://docs.astral.sh/uv/), a Pipefy service account, plus **Cursor** and **NVIDIA** API keys for `make tour` (Act 2 and Act 3).

1. Clone, `cp .env.example .env`, and fill credentials ([`.env.example`](.env.example)).
2. Run the **Run this first** block above (install targets → `make doctor` → `make tour`).
3. Optional deep dive: **[docs/TRY_IT_YOURSELF.md](docs/TRY_IT_YOURSELF.md)**.

The tour is a three-act story over the same Pipefy data:

- **Act 1** — Query **Pipefy** with the `pipefy` CLI (deterministic ground truth).
- **Act 2** — Run a **Cursor SDK** agent against the same data via **Pipefy MCP**.
- **Act 3** — Run **NeMo Agent Toolkit** with **NIM** against the same MCP tools.

### Reliability contract (read before `make tour`)

- **Act 2 (Cursor)** is the **guaranteed-green** path.
- **Act 3 (NAT, 8b)** is **best-effort**: `meta/llama-3.1-8b-instruct` is a small model on a multi-step task, so the tour retries it (compare-gated, up to 3×). For a more reliable first attempt, set `NIM_MODEL=meta/llama-3.1-70b-instruct` if your NVIDIA tier allows (opt-in; see [OPEN_DECISIONS.md](docs/OPEN_DECISIONS.md) D18/D19).
- **Encore:** `make tour` ends with an automated fact check (`eval/compare.py`) comparing harness answers to the CLI baseline — not a fourth agent.

Build-time discoveries (Pipefy pagination/truncation, Cursor/NAT quirks) are documented in **[docs/LEARNINGS.md](docs/LEARNINGS.md)**.

## Documentation

| Document | Purpose |
|----------|---------|
| **[docs/README.md](docs/README.md)** | Documentation index and cross-reference map |
| **[docs/TRY_IT_YOURSELF.md](docs/TRY_IT_YOURSELF.md)** | Hands-on tour (primary runbook) |
| **[docs/ARCHITECTURE_AND_IMPLEMENTATION_PLAN.md](docs/ARCHITECTURE_AND_IMPLEMENTATION_PLAN.md)** | Architecture, decisions, delivery phases |
| **[docs/LEARNINGS.md](docs/LEARNINGS.md)** | Operational learnings (Pipefy truncation, Cursor/NAT quirks, tour/Encore) |
| **[docs/BENCHMARKS.md](docs/BENCHMARKS.md)** | Reliability & latency numbers (operator-reproducible) |
| **[docs/CLOUD.md](docs/CLOUD.md)** | Cursor Cloud agent setup and run |
| **[docs/OPEN_DECISIONS.md](docs/OPEN_DECISIONS.md)** | Resolved and open decisions |
| [.env.example](.env.example) | API keys and demo pipe configuration |

## Related projects

| Project | Role |
|---------|------|
| [pipefy/ai-toolkit](https://github.com/pipefy/ai-toolkit) | **Official Pipefy AI Toolkit**: `pipefy-mcp-server`, `pipefy` CLI, GraphQL SDK, agent skills |
| [Cursor Python SDK](https://cursor.com/docs/sdk/python) | Programmatic **Cursor** agent (`cursor-sdk`) |
| [NVIDIA NeMo Agent Toolkit](https://github.com/NVIDIA/NeMo-Agent-Toolkit) ([docs](https://docs.nvidia.com/nemo/agent-toolkit/latest/index.html)) | **NVIDIA** YAML workflows, MCP client, NIM, profiler, evaluation (`nvidia-nat`, Apache-2.0) |
