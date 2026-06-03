# pipefy-agent-bridge

A public **reference implementation** that connects **Pipefy** operations to AI agents through a single **Model Context Protocol (MCP)** tool layer—then orchestrates that layer with both the **Cursor SDK** and the **NVIDIA NeMo Agent Toolkit (NAT)** + **NIM**.

> **Disclaimer:** Community-maintained software. Not an official Pipefy, Cursor, or NVIDIA product.

## Quick start

**Goal:** Run the **Pipefy → Cursor → NVIDIA** flow on your machine in about 20–30 minutes.

1. Clone this repository and copy `.env.example` → `.env`.
2. Follow the guided tour: **[docs/TRY_IT_YOURSELF.md](docs/TRY_IT_YOURSELF.md)**

You will:

- **Act 1** — Query **Pipefy** with the `pipefy` CLI (deterministic ground truth).
- **Act 2** — Run a **Cursor SDK** agent against the same data via **Pipefy MCP**.
- **Act 3** — Run **NeMo Agent Toolkit** with **NIM** against the same MCP tools.

Shipped Makefile targets: `make doctor`, `make install-pipefy-tools`, `make install-cursor-demo`, `make install-nat-demo`, `make demo-cursor`, `make demo-nat`, `make tour`. Run the full tour after both harness installs and a filled `.env` (see [TRY_IT_YOURSELF](docs/TRY_IT_YOURSELF.md)).

### Known limitations (read before `make tour`)

We document build-time discoveries in **[docs/LEARNINGS.md](docs/LEARNINGS.md)**. Short version:

| Layer | Limitation | Why |
|-------|------------|-----|
| **Pipefy CLI** | `pipesCount` may be org-wide while `pipes[]` is a truncated page (`pipes_truncated: true`). | Large orgs return a sample, not every pipe in one JSON blob. |
| **Cursor** | Usually reliable for `inventory`; may mention both “5 visible pipes” and org total. | Model summarizes MCP results; Encore compare uses the **listed** pipes. |
| **NVIDIA NAT (8b)** | `meta/llama-3.1-8b-instruct` can miss tools, hit recursion limits, or emit incomplete `Final Answer`s. | Small model + multi-step inventory (search + per-pipe card counts). Tour retries NAT up to 3×; consider `70b` for demos (see LEARNINGS). |

**Encore:** `make tour` ends with an automated fact check (`eval/compare.py`) that compares harness answers to the CLI baseline—not a fourth agent.

**Tour status:** With valid credentials, `make tour` is intended to exit `0` after Acts 1–3; Act 3 may run NAT up to **3×** (compare-gated) before Encore—see [LEARNINGS](docs/LEARNINGS.md) if Act 3 or Encore fails on the first try.

**Reliability contract:** **Act 2 (Cursor)** is the guaranteed-green path; **Act 3 (NAT, 8b)** is **best-effort** (retried, compare-gated). For a more reliable first attempt, set `NIM_MODEL=meta/llama-3.1-70b-instruct` if your NVIDIA tier allows (opt-in; see [OPEN_DECISIONS.md](docs/OPEN_DECISIONS.md) D18/D19). First-attempt NAT reliability is a measured objective in [PRD-2](product/prd/prd-2-nat-profiler-and-evaluation.md).

## Documentation

| Document | Purpose |
|----------|---------|
| **[docs/README.md](docs/README.md)** | Documentation index and cross-reference map |
| **[docs/TRY_IT_YOURSELF.md](docs/TRY_IT_YOURSELF.md)** | Hands-on tour (primary runbook) |
| **[docs/LEARNINGS.md](docs/LEARNINGS.md)** | **Operational learnings** (Pipefy truncation, Cursor/NAT quirks, tour/Encore) |
| **[docs/ARCHITECTURE_AND_IMPLEMENTATION_PLAN.md](docs/ARCHITECTURE_AND_IMPLEMENTATION_PLAN.md)** | Architecture, decisions, phases, tasks |
| **[docs/OPEN_DECISIONS.md](docs/OPEN_DECISIONS.md)** | Resolved and open decisions |
| [.env.example](.env.example) | API keys and demo pipe configuration |

## Repository layout

```
pipefy-agent-bridge/
├── configs/          # NAT workflow, MCP tool allowlist
├── demos/            # Cursor SDK + NAT smoke scripts, prompts
├── docs/             # All documentation (incl. LEARNINGS.md)
├── eval/             # CLI ground truth, compare.py, fixtures
├── private/          # Local CONTEXT.md (gitignored); see CONTEXT.md.example
├── README.md
├── LICENSE           # MIT
└── .env.example
```

## Related projects

| Project | Role |
|---------|------|
| [pipefy/ai-toolkit](https://github.com/pipefy/ai-toolkit) | **Official Pipefy AI Toolkit**: `pipefy-mcp-server`, `pipefy` CLI, GraphQL SDK, agent skills |
| [Cursor Python SDK](https://cursor.com/docs/sdk/python) | Programmatic **Cursor** agent (`cursor-sdk`) |
| [NVIDIA NeMo Agent Toolkit](https://github.com/NVIDIA/NeMo-Agent-Toolkit) ([docs](https://docs.nvidia.com/nemo/agent-toolkit/latest/index.html)) | **NVIDIA** YAML workflows, MCP client, NIM, profiler, evaluation (`nvidia-nat`, Apache-2.0) |

## License

[MIT](LICENSE) — see [OPEN_DECISIONS.md](docs/OPEN_DECISIONS.md) (D1, resolved).
