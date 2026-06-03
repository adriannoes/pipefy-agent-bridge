# Pipefy Agent Bridge — Architecture & Implementation Plan

**Repository:** `pipefy-agent-bridge`  
**Version:** 0.5 (planning)  
**Audience:** Implementers breaking this document into tasks; anyone evaluating the architecture  
**Language:** English (implementation artifacts may mix English docs with Portuguese demo notes if desired)

---

## Table of contents

1. [Executive summary](#1-executive-summary)
2. [Goals, non-goals, and success criteria](#2-goals-non-goals-and-success-criteria)
3. [Technology landscape and fluency narrative](#3-technology-landscape-and-fluency-narrative)
4. [Problem statement](#4-problem-statement)
5. [Architectural overview](#5-architectural-overview)
6. [Core design decision: MCP as the single tool contract](#6-core-design-decision-mcp-as-the-single-tool-contract)
7. [Component responsibilities](#7-component-responsibilities)
8. [Dual harness strategy: Cursor SDK and NVIDIA NeMo Agent Toolkit](#8-dual-harness-strategy-cursor-sdk-and-nvidia-nemo-agent-toolkit)
9. [Pipefy CLI role (ground truth, not primary agent interface)](#9-pipefy-cli-role-ground-truth-not-primary-agent-interface)
10. [Authentication and security](#10-authentication-and-security)
11. [NVIDIA stack: what we use and what we deliberately avoid](#11-nvidia-stack-what-we-use-and-what-we-deliberately-avoid)
12. [Optional phase: GPU embeddings and semantic search](#12-optional-phase-gpu-embeddings-and-semantic-search)
13. [Repository layout (target structure)](#13-repository-layout-target-structure)
14. [Phased delivery plan](#14-phased-delivery-plan)
15. [Hands-on scenarios (reproducible locally)](#15-hands-on-scenarios-reproducible-locally)
16. [Operator experience: explained, reproducible, not video-first](#16-operator-experience-explained-reproducible-not-video-first)
17. [Evaluation strategy](#17-evaluation-strategy)
18. [Operational concerns](#18-operational-concerns)
19. [Risks and mitigations](#19-risks-and-mitigations)
20. [Task breakdown hints (for issue tracking)](#20-task-breakdown-hints-for-issue-tracking)
21. [References](#21-references)

See also: [docs/README.md](README.md) (documentation index) · [OPEN_DECISIONS.md](OPEN_DECISIONS.md) (deferred choices)

---

## 1. Executive summary

**Pipefy Agent Bridge** is a small, public reference repository that demonstrates how to operate **Pipefy** (work management / process orchestration) through AI agents using industry-standard **Model Context Protocol (MCP)** tools, with **two complementary orchestration harnesses**:

1. **Cursor SDK** (`cursor-sdk`, Python) — the same class of programmatic agent harness that powers Cursor IDE, CLI, and Cloud Agents; ideal for developer-centric automation, multi-turn sessions, and showcasing deep understanding of **Cursor** agent lifecycle APIs.
2. **NVIDIA NeMo Agent Toolkit (NAT)** (`nvidia-nat`, with `[mcp]` extras) — NVIDIA’s framework-agnostic toolkit for building, profiling, evaluating, and operating agent workflows; ideal for demonstrating **NVIDIA** fluency (NIM LLMs, MCP client configuration, profiler, evaluation hooks) without reimplementing Pipefy integrations.

Both harnesses consume the **same Pipefy MCP server** from the **official Pipefy AI Toolkit** [**pipefy/ai-toolkit**](https://github.com/pipefy/ai-toolkit) (`pipefy-mcp-server` + `pipefy` CLI + `pipefy-sdk`). This repository does **not** duplicate Pipefy API logic; it **bridges** Pipefy capabilities to Cursor and NVIDIA agent runtimes.

The name **bridge** is intentional: one stable tool surface (MCP), multiple agent runtimes (Cursor, NVIDIA NAT).

---

## 2. Goals, non-goals, and success criteria

### 2.1 Goals

| ID | Goal | Why it matters |
|----|------|----------------|
| G1 | **Working end-to-end walkthrough** | Anyone can clone the repo, set env vars, run scripts, and see real Pipefy data accessed via agents. |
| G2 | **Demonstrate Cursor SDK mastery** | Show `Agent.create`, MCP `stdio` configuration, `send` / `wait`, error handling (`CursorAgentError` vs `result.status`), and explicit `local` runtime selection. |
| G3 | **Demonstrate NVIDIA NAT mastery** | Show YAML workflow, `mcp_client` function group with `stdio` transport, NIM LLM, `nat run`, profiler (`make profile-nat`), and eval runner (`make eval`; Phase 5). |
| G4 | **Demonstrate Pipefy domain fluency** | Scenarios reflect real ops work: pipe inventory, phase backlog, stale cards, safe card transitions—not toy “hello world” APIs. |
| G5 | **Reproducibility** | Pipefy CLI `--json` outputs provide deterministic ground truth comparable to agent answers. |
| G6 | **Public reference repo** | Clear README, documentation index, `.env.example`, and a **hands-on tour** runnable locally in ~20–30 minutes. |
| G7 | **Operator-friendly UX** | `make doctor`, `make tour`, plain-language “what you should see,” troubleshooting—no video required to validate the stack. |

### 2.2 Non-goals

| ID | Non-goal | Justification |
|----|----------|---------------|
| NG1 | Official Pipefy product | This bridge repo is not an official Pipefy product; the upstream toolkit (`pipefy/ai-toolkit`) is Pipefy-official, but orchestration here is community/demo. Keep the disclaimer in README. |
| NG2 | Replacing pipefy-mcp-server | That repo is the canonical tool/SDK layer; this repo is orchestration + demo only. |
| NG3 | Single merged Python process for Cursor + NAT | Two entrypoints keep concerns separable and easier to debug. |
| NG4 | Exposing all 149 MCP tools to NAT at once | Tool sprawl degrades LLM tool selection; curate an `include` list. |
| NG5 | Forcing CUDA on every GraphQL call | Not credible; GPU is reserved for embedding/RAG phase (optional). |
| NG6 | Production multi-tenant SaaS | Out of scope for this reference repo; document security boundaries instead. |

### 2.3 Success criteria (definition of done)

- [x] `demos/01_cursor_pipefy_ops.py` completes a scripted Pipefy query via **Cursor SDK** + **Pipefy MCP**.
- [x] `make demo-nat` (or documented `nat run`) completes the **same class of query** via **NVIDIA NAT** + **Pipefy MCP** + **NIM**.
- [x] README and **[TRY_IT_YOURSELF.md](TRY_IT_YOURSELF.md)** list install steps for `pipefy-mcp-server` / `make install-*` and env vars (`.env.example`).
- [x] An operator with credentials can complete **[TRY_IT_YOURSELF.md](TRY_IT_YOURSELF.md)** Steps 0–4 on a clean machine in ~20–30 minutes.
- [x] `make doctor` and `make tour` exist and are documented in README / TRY_IT_YOURSELF.
- [x] At least **three hands-on scenarios** (Section 15) run via `make demo-cursor SCENARIO=...` and `make demo-nat SCENARIO=...`.
- [x] At least **one evaluation check** compares NAT/Cursor output to **Pipefy CLI** JSON (Section 17; `make tour` + `eval/compare.py` on `inventory`).
- [ ] Optional: asciinema linked from README for users who cannot run locally (secondary artifact).

---

## 3. Technology landscape and fluency narrative

This project is designed so readers can see **intentional, complementary use** of three ecosystems—not three buzzwords bolted together.

### 3.1 Pipefy

**Pipefy** is a work management platform where teams model processes as **pipes**, **phases**, and **cards** (with typed fields, automations, portals, and organization-level reporting). Developer-facing access is primarily **GraphQL**.

**Our position:** Business logic and API access live in the official Pipefy AI Toolkit [**pipefy/ai-toolkit**](https://github.com/pipefy/ai-toolkit), a `uv` workspace:

- **`pipefy-sdk`** — vendor GraphQL client, services, Pydantic models.
- **`pipefy-mcp-server`** — **149 MCP tools across ten domains** (pipes/cards, database tables, relations, reports, automations & AI, etc.); canonical names in `PIPEFY_TOOL_NAMES` (`packages/mcp/src/pipefy_mcp/tools/registry.py`).
- **`pipefy` CLI** (`pipefy-cli`) — terminal commands with MCP parity documented in `docs/parity.md`.

**Pipefy Agent Bridge** assumes Pipefy expertise is proven through **realistic workflows** (triage, SLA-style staleness, summaries)—not through re-copying GraphQL queries in this repo.

### 3.2 Cursor

**Cursor** is an AI-native development environment; its **Cursor SDK** (`cursor-sdk` on PyPI) exposes the **same agent** that runs in the IDE/CLI as a programmable API:

- **Agent** — durable handle (conversation, model, MCP config).
- **Run** — one prompt execution with streaming and terminal status.
- **MCP** — inline `StdioMcpServerConfig` / `HttpMcpServerConfig` on `Agent.create()` or per-`send()`.

**Our position:** Cursor is the **developer harness** story: “I know how to wire MCP tools, manage agent lifecycle, distinguish startup failures from run failures, and run agents locally against a workspace.” See [Cursor Python SDK documentation](https://cursor.com/docs/sdk/python).

### 3.3 NVIDIA

**NVIDIA NeMo Agent Toolkit (NAT)** is a framework-agnostic library for connecting agents to data sources and tools, with first-class **MCP client** support, **NIM** LLM integration, **profiling**, **observability**, and **evaluation**. See [NeMo Agent Toolkit overview](https://docs.nvidia.com/nemo/agent-toolkit/latest/index.html).

**Our position:** NVIDIA is the **operations and measurement** story: “I can run the same Pipefy tools under a YAML-defined workflow, use **NIM** models via `NVIDIA_API_KEY`, and profile/evaluate agent behavior—not only prototype in an IDE.”

**CUDA / CUDA-X** libraries ([CUDA-X libraries](https://developer.nvidia.com/cuda/cuda-x-libraries)) enter only in the **optional** semantic-search phase (embeddings + vector search), where GPU acceleration is technically honest.

---

## 4. Problem statement

Teams using **Pipefy** repeatedly perform operational tasks:

- Finding cards stuck in a phase beyond an SLA threshold.
- Summarizing backlog across pipes or phases.
- Validating field values before phase transitions.
- Cross-checking automation or AI agent configuration (Pipefy product feature) against live pipe state.

These tasks are tedious in the UI and error-prone when done manually at scale. **AI agents** can help if they have:

1. **Safe, typed tools** (MCP) instead of ad-hoc shell scripts.
2. **A reliable harness** for multi-step reasoning (Cursor SDK for dev workflows; NAT for measured workflows).
3. **Ground truth** for validation (Pipefy CLI JSON).

Without a **bridge**, every team reinvents: GraphQL clients, auth, tool schemas, and one-off LangChain scripts. This repo shows a **reference pattern** endorsed by both **Cursor** (SDK + MCP) and **NVIDIA** (NAT MCP client).

---

## 5. Architectural overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     pipefy-agent-bridge (this repo)                      │
│  demos/ · configs/ · eval/ · docs/ — orchestration & validation only    │
└─────────────────────────────────────────────────────────────────────────┘
         │                                    │
         │ Cursor SDK                         │ NVIDIA NAT (nat run)
         ▼                                    ▼
┌─────────────────────┐              ┌─────────────────────┐
│  cursor-sdk Agent   │              │  react_agent workflow│
│  local runtime      │              │  + nim LLM (NIM)     │
│  mcp_servers:       │              │  function_groups:    │
│    pipefy (stdio)   │              │    mcp_client stdio  │
└──────────┬──────────┘              └──────────┬──────────┘
           │                                    │
           └────────────────┬───────────────────┘
                            │ MCP (stdio): pipefy-mcp-server
                            ▼
           ┌────────────────────────────────────────────┐
           │  pipefy/ai-toolkit (official, external)     │
           │  pipefy-mcp-server · pipefy CLI · pipefy-sdk │
           └────────────────────┬───────────────────────┘
                                │ GraphQL
                                ▼
                        ┌───────────────┐
                        │    Pipefy     │
                        │  (SaaS API)   │
                        └───────────────┘

Parallel ground-truth path (no LLM):

  pipefy CLI --json  ──►  same GraphQL via pipefy-sdk
```

### 5.1 Data flow (typical agent query)

1. Human or CI invokes **Cursor demo script** or **`nat run`** with a natural-language prompt.
2. Harness selects tools from **Pipefy MCP** (e.g., `list_pipes`, `list_cards`, `get_card`).
3. MCP server calls **pipefy-sdk** → **Pipefy GraphQL API**.
4. Harness synthesizes a natural-language answer (Cursor model or **NIM**).
5. Optional: **eval** script compares key facts to **`pipefy … --json`** output.

### 5.2 Why two harnesses in one repo

| Concern | Cursor SDK | NVIDIA NAT |
|---------|------------|------------|
| Typical operator | Platform / developer automation | ML ops / agent workflow engineering |
| LLM backend | Cursor-managed models (e.g., `composer-2.5`) | **NIM** on build.nvidia.com |
| Config style | Python code | Declarative YAML |
| Strength | IDE-adjacent dev automation, cloud agents | Profiling, evaluation, `nat serve` |
| Shared dependency | **Pipefy MCP** | **Pipefy MCP** |

Using both proves the integrator understands **MCP as the portability layer**—a pattern NVIDIA documents explicitly for NAT ([MCP client guide](https://docs.nvidia.com/nemo/agent-toolkit/latest/build-workflows/mcp-client.html)) and Cursor documents for the SDK ([MCP servers](https://cursor.com/docs/sdk/python#mcp-servers)).

---

## 6. Core design decision: MCP as the single tool contract

### 6.1 Decision

All agent-driven Pipefy operations go through **`pipefy-mcp-server`** (stdio MCP), not direct subprocess calls to `pipefy` from the LLM loop.

### 6.2 Justification

| Alternative | Rejected because |
|-------------|------------------|
| LLM invokes `pipefy` via shell | Fragile parsing; harder tool discovery; weak schema contracts; weak reproducibility story. |
| Duplicate GraphQL in this repo | Violates DRY; diverges from pipefy-mcp-server; high maintenance. |
| NAT custom `@register_function` per Pipefy op | Reimplements 149 tools; MCP already registered and documented. |
| HTTP MCP only | Stdio is sufficient for local demo; pipefy-mcp-server defaults to stdio; simpler secrets on laptop. |

### 6.3 Cursor SDK alignment

Cursor’s Python SDK accepts inline MCP servers on `Agent.create()`:

```python
mcp_servers={
    "pipefy": StdioMcpServerConfig(
        command="pipefy-mcp-server",
        env={...},
    ),
}
```

**Justification:** Inline servers are explicit (no accidental loading of user `~/.cursor/mcp.json` unless `setting_sources` is opted in). For demos, **explicit is better than implicit** per Cursor SDK production guidance.

### 6.4 NVIDIA NAT alignment

NAT `mcp_client` function groups support **stdio** transport with `command` / `args` / `env` ([transport configuration](https://docs.nvidia.com/nemo/agent-toolkit/latest/build-workflows/mcp-client.html)):

```yaml
function_groups:
  pipefy:
    _type: mcp_client
    server:
      transport: stdio
      command: pipefy-mcp-server
      env: ...
```

**Justification:** Same binary as Cursor—operators can trace one MCP process in `ps` during the tour.

### 6.5 Tool curation (`include` list)

pipefy-mcp-server registers **149 tools across ten domains** (confirm on the pinned version). NAT workflows should pass `include:` with **8–15 tools** for MVP (inventory + read + one safe write).

**Justification:** ReAct-style agents degrade with oversized tool catalogs (wrong tool choice, higher latency). Expand `include` incrementally per demo scenario.

**Suggested MVP tool names** (verify against `PIPEFY_TOOL_NAMES` in `pipefy/ai-toolkit` → `packages/mcp/src/pipefy_mcp/tools/registry.py`):

- Introspection: `get_pipe`, `list_pipes` (exact names may differ—validate at implementation time).
- Cards: `list_cards`, `get_card`, `move_card_to_phase` (only if demo org allows writes).
- Organization: organization metadata tool if multi-pipe discovery needs it.

> **Implementation task:** Run `nat mcp client tool list` or MCP Inspector against `pipefy-mcp-server` and freeze the MVP list in `configs/tool_allowlist.yml`.

---

## 7. Component responsibilities

### 7.1 pipefy/ai-toolkit (external dependency)

| Responsibility | Owner |
|----------------|--------|
| GraphQL auth (OAuth human, service account, token precedence) | pipefy-mcp-server |
| MCP tool schemas and docstrings | pipefy-mcp-server |
| CLI parity with MCP | pipefy-mcp-server |
| Agent skills (Markdown playbooks) | pipefy-mcp-server `skills/` |

**Install (pre-1.0):** Follow the [pipefy/ai-toolkit README](https://github.com/pipefy/ai-toolkit#installation) — either the official `install.sh` (`--client cursor`) or `uv tool install` with workspace-member pins (`pipefy-sdk`, `pipefy-auth` via `#subdirectory=packages/...`) until PyPI v1.0.

**This repo** documents the required version tag (e.g., `@v0.2.0-beta.2`) in README for reproducibility; avoid the moving `@latest` tag.

### 7.2 pipefy-agent-bridge (this repo)

| Responsibility | Owner |
|----------------|--------|
| Cursor SDK demo scripts | `demos/` |
| NAT workflow YAML | `configs/` |
| Evaluation vs CLI | `eval/` |
| Architecture & runbooks | `docs/` |
| Makefile / task runner | root |

### 7.3 Cursor SDK harness

| Responsibility | Details |
|----------------|---------|
| Agent lifecycle | `with Agent.create(...) as agent:` — always dispose |
| Runtime | **Always** set `local=LocalAgentOptions(cwd=...)` explicitly (avoid silent default confusion) |
| Model | `model="composer-2.5"` or list via `Cursor.models.list()` |
| Errors | Exit 1 on `CursorAgentError`; exit 2 on `result.status == "error"` |
| MCP | `pipefy` stdio server; service account env vars |
| Logging | Log `agent.agent_id` and `run.id` after `send()` |

### 7.4 NVIDIA NAT harness

| Responsibility | Details |
|----------------|---------|
| Package | `pip install "nvidia-nat[mcp]"` (or `uv pip install`) |
| LLM | `_type: nim` with `model_name` and `NVIDIA_API_KEY` |
| Workflow | `_type: react_agent` with `tool_names: [pipefy]` and `llm_name` pointing at the `nim` LLM |
| CLI | `nat run --config_file configs/pipefy_nat_workflow.yml --input "..."` |
| Phase 5 | Shipped: `make profile-nat`, `make eval`, `eval/golden.yaml`, [`docs/BENCHMARKS.md`](BENCHMARKS.md) (dated 2026-06-03 measured run) |

---

## 8. Dual harness strategy: Cursor SDK and NVIDIA NeMo Agent Toolkit

### 8.1 Decision

Implement **two entrypoints**, not a unified abstraction layer.

### 8.2 Justification

- **Separation of concerns:** Operators can run `python demos/01_cursor_pipefy_ops.py` without installing NAT.
- **Optional NVIDIA-only path:** Operators can run `nat run` without a Cursor API key (only `NVIDIA_API_KEY` + Pipefy credentials).
- **Honest scope:** A thin “unified SDK” would be over-engineering for a demo repo (violates minimal-scope principle).

### 8.3 Cursor SDK — implementation notes

**Pattern:** `Agent.create` + `agent.send` + `run.wait()` (streaming optional for demos).

**One-shot alternative:** `Agent.prompt()` only for CI smoke tests—it disposes automatically but offers less observability.

**Cloud agents:** Optional stretch goal (`CloudAgentOptions` + `repos=[...]`) to run Pipefy automation in Cursor Cloud VMs. **Not MVP**—requires cloning this repo to GitHub and SCM integration. Document as Phase 4.

**MCP on resume:** Cursor does not persist inline MCP across `Agent.resume()`; demos should not rely on resume unless MCP is re-passed.

References:

- [Cursor Python SDK](https://cursor.com/docs/sdk/python)
- MCP inline config: `StdioMcpServerConfig`, `env` for service account secrets

### 8.4 NVIDIA NAT — implementation notes

**Pattern:** YAML `workflow.yml` + `nat run`.

**MCP install:** `nvidia-nat[mcp]` per [NAT MCP workflows](https://docs.nvidia.com/nemo/agent-toolkit/latest/workflows/mcp/index.html).

**Model choice:** Start with `meta/llama-3.1-8b-instruct` for speed/cost; upgrade to `meta/llama-3.1-70b-instruct` for harder reasoning demos.

**Verbose:** `verbose: true` in workflow for demo recordings.

**Serving (optional):** `nat mcp serve` exposes a workflow as MCP—useful if you later want Cursor to call a NAT-wrapped workflow. **Not required** for MVP; note as future architecture spike.

References:

- [NAT MCP client](https://docs.nvidia.com/nemo/agent-toolkit/latest/build-workflows/mcp-client.html)
- [NAT overview](https://docs.nvidia.com/nemo/agent-toolkit/latest/index.html)

### 8.5 Comparing harness outputs

For the same prompt class, expect **semantic equivalence**, not byte-identical strings:

- Cursor may use **Composer**; NAT uses **NIM**.
- Tool call order may differ.

Eval should compare **structured facts** (counts, IDs, phase names) extracted from CLI JSON vs agent answer (manual rubric or light LLM-judge—keep MVP simple).

---

## 9. Pipefy CLI role (ground truth, not primary agent interface)

### 9.1 Decision

Use **`pipefy` CLI** with `--json` in `eval/` and README examples; do **not** wire CLI as the LLM’s primary tool interface.

### 9.2 Justification

| Role | CLI | MCP |
|------|-----|-----|
| Agent tool surface | No | Yes |
| Deterministic CI checks | Yes | Possible but heavier |
| Human debugging | Yes | MCP Inspector |
| Parity documentation | `docs/parity.md` in pipefy/ai-toolkit | Tool registry |

Example ground-truth command (illustrative—confirm exact subcommand in parity matrix):

```bash
pipefy pipe list --json
pipefy card get <CARD_ID> --json
```

**Justification:** Separates **agent probabilistic layer** from **deterministic verification**—a production mindset aligned with NeMo Agent Toolkit evaluation docs.

---

## 10. Authentication and security

### 10.1 Decision

Default demo auth: **Pipefy service account** (`PIPEFY_SERVICE_ACCOUNT_CLIENT_ID` / `PIPEFY_SERVICE_ACCOUNT_CLIENT_SECRET`) injected into MCP stdio `env`.

### 10.2 Justification

| Method | Use case |
|--------|----------|
| Service account | Unattended demos, CI, screen recording without browser |
| Human OAuth (`pipefy auth login`) | Local dev when service account provisioning is slow |
| `PIPEFY_TOKEN` | Short-lived debugging only; document precedence from pipefy/ai-toolkit `packages/cli/README.md` |

### 10.3 Secret handling

| Secret | Storage |
|--------|---------|
| `CURSOR_API_KEY` | `.env` (gitignored); never commit |
| `NVIDIA_API_KEY` | `.env` (gitignored) |
| Pipefy service account | `.env` (gitignored); passed to MCP child process env |
| Demo pipe IDs | `.env.example` placeholders only |

**Cursor cloud `env_vars`:** If using Cloud agents later, use `CloudAgentOptions.env_vars` for session-scoped secrets (encrypted at rest per Cursor docs)—not needed for local MVP.

### 10.4 Blast radius

- Create a **dedicated Pipefy organization or sandbox** for demos.
- Service account granted **minimum pipes** (e.g., one demo pipe).
- Write demos (`move_card_to_phase`) behind explicit env flag `DEMO_ALLOW_WRITES=true`.

### 10.5 Disclaimer

Repeat in README: community demo; not official Pipefy endorsement. Align with pipefy-mcp-server disclaimer.

---

## 11. NVIDIA stack: what we use and what we deliberately avoid

### 11.1 In scope (MVP + Phase 5)

| NVIDIA technology | Usage |
|-------------------|--------|
| **NeMo Agent Toolkit** | Orchestration, MCP client, `nat run`, profiler (`make profile-nat`), eval runner (`make eval`) |
| **NIM** | LLM via `_type: nim` and `NVIDIA_API_KEY` |
| **MCP integration** | `nvidia-nat[mcp]` package |

### 11.2 Out of scope (MVP)

| Technology | Why deferred |
|------------|--------------|
| **TensorRT-LLM** custom serving | NIM already abstracts inference for demo |
| **CUDA kernels in GraphQL path** | No compute-bound numerical work in API calls |
| **Dynamo** | Advanced scale-out; unnecessary for single-user demo |
| **Full RAG platform** | Unless Phase 7 embeddings is pursued |

### 11.3 Optional in scope (Phase 7) — honest GPU story

If time permits, add **`embeddings/`** module:

1. Fetch card titles/descriptions via MCP or CLI.
2. Compute embeddings with **NVIDIA NIM embedding model** or NeMo Embeddings API.
3. Index with **FAISS** or **cuVS** ([CUDA-X](https://developer.nvidia.com/cuda/cuda-x-libraries)) for “find similar cards.”

**Justification:** This is where GPU acceleration is **credible**—batch linear algebra over text vectors—not where you mutate a single card via GraphQL.

---

## 12. Optional phase: GPU embeddings and semantic search

### 12.1 User-facing capability

> “Find cards semantically similar to this bug report” across a demo pipe with hundreds of cards.

### 12.2 Architecture add-on

```
Pipefy cards (CLI/MCP) → text fields → NIM embeddings → GPU vector index → top-k results → agent summarizes
```

### 12.3 Dependencies

- `NVIDIA_API_KEY` with embedding model access
- Python deps: `faiss-gpu` or RAPIDS/cuVS per environment support
- Document CPU fallback for machines without NVIDIA GPUs

### 12.4 Task gate

Do not start Phase 7 until MVP Cursor + NAT demos are green.

---

## 13. Repository layout (target structure)

```
pipefy-agent-bridge/
├── README.md
├── LICENSE
├── Makefile
├── pyproject.toml              # optional: shared dev deps (ruff, pytest)
├── .env.example
├── .gitignore
├── configs/
│   ├── pipefy_nat_workflow.yml # NAT react_agent + mcp_client + nim
│   └── tool_allowlist.yml      # curated MCP tool names (generated/verified)
├── demos/
│   ├── 01_cursor_pipefy_ops.py
│   ├── 02_nat_smoke.sh         # wraps nat run
│   └── prompts/
│       ├── inventory.txt
│       ├── stale_cards.txt
│       └── summary.txt
├── eval/
│   ├── ground_truth.sh         # pipefy CLI JSON snapshots
│   ├── compare.py              # lightweight fact checker (shipped MVP)
│   ├── fixtures/               # JSON baselines: example/ committed, live/ gitignored (D13)
│   └── transcripts/            # saved agent runs for manual review (gitignored)
├── docs/
│   ├── README.md               # documentation index
│   ├── ARCHITECTURE_AND_IMPLEMENTATION_PLAN.md  # this file
│   ├── TRY_IT_YOURSELF.md      # primary hands-on tour (Pipefy → Cursor → NVIDIA)
│   └── OPEN_DECISIONS.md       # deferred implementation choices
├── private/
│   ├── CONTEXT.md.example      # template for gitignored local notes
│   └── CONTEXT.md              # gitignored — maintainer context only
└── embeddings/                 # Phase 7 only
    └── README.md
```

**Justification:** Separating `demos/`, `configs/`, and `eval/` maps 1:1 to task boards (Cursor / NVIDIA / QA).

---

## 14. Phased delivery plan

> **MVP status (Phases 0–4 shipped):** Upstream pinned at **`pipefy/ai-toolkit@v0.2.0-beta.2`** (`PIPEFY_TOOLKIT_REF` in `Makefile`; mirrored in `configs/tool_allowlist.yml` as `pipefy_toolkit_ref`). **`configs/tool_allowlist.yml`** curates **12** MCP tool names (verified with `nat mcp client tool list --transport stdio --command pipefy-mcp-server` for that tag). NAT workflow uses **`meta/llama-3.1-8b-instruct`** on NIM and an **inventory-only 2-tool** `include:` (`search_pipes`, `get_cards`) in `configs/pipefy_nat_workflow.yml` (§16.5). Phases 5–7 remain stretch.

### Phase 0 — Repository scaffolding (day 0) — **shipped**

- [x] Git init, README, `.env.example`, this document
- [x] Choose license (**MIT** — see [OPEN_DECISIONS.md](OPEN_DECISIONS.md) D1)
- [x] Add `Makefile` with `help`, `doctor`, `install-*`, `demo-cursor`, `demo-nat`, `tour` (CLI baselines via `eval/ground_truth.sh`, not a separate `eval-baseline` target)
- [x] `pyproject.toml`, `uv.lock`, lint-only CI (`.github/workflows/ci.yml`)

**Exit criteria:** [x] `LICENSE` present; [x] `make help` lists operator targets; [ ] repository initial commit (task 6.4 close-out).

### Phase 1 — Pipefy tool chain verified (day 1) — **shipped**

**Objective:** Prove Pipefy MCP and CLI work independently of agents.

Tasks:

1. [x] Install `pipefy-mcp-server` and `pipefy` CLI from [pipefy/ai-toolkit](https://github.com/pipefy/ai-toolkit) @ **`v0.2.0-beta.2`** (`make install-pipefy-tools`; `uv tool install` with workspace-member pins).
2. [x] Configure service account; set `DEMO_PIPE_ID`, `DEMO_ORG_ID`, `DEMO_PHASE_NAME` (`.env.example`; validated by `make doctor`).
3. [x] Read-only ping: `pipefy pipe list --json` in `scripts/doctor.sh` (non-empty pipe list).
4. [ ] *(Optional operator step)* MCP Inspector: `npx @modelcontextprotocol/inspector` with `pipefy-mcp-server` — not automated in repo.
5. [x] Freeze **12** tool names into `configs/tool_allowlist.yml` (consumed by NAT `include:`).

**Exit criteria:** [x] `make doctor` passes with Pipefy credentials; [x] allowlist names resolve on the pinned MCP server.

### Phase 2 — Cursor SDK harness (day 2) — **shipped**

**Objective:** Programmatic **Cursor** agent with **Pipefy MCP**.

Tasks:

1. [x] `make install-cursor-demo` — `cursor-sdk==0.1.6`, `python-dotenv==1.2.2` (documented in TRY_IT_YOURSELF).
2. [x] `demos/01_cursor_pipefy_ops.py` — dotenv, `Agent.create` + `StdioMcpServerConfig`, stream tool calls, exit codes 0/1/2.
3. [x] Prompt files: `demos/prompts/inventory.txt`, `stale_cards.txt`, `summary.txt`.
4. [x] Log `agent_id` and `run.id`; `make demo-cursor` with `SCENARIO=`.

**Exit criteria:** [x] `make demo-cursor SCENARIO=inventory` returns a coherent org-wide pipe inventory aligned with CLI ground truth.

### Phase 3 — NVIDIA NAT harness (day 3) — **shipped**

**Objective:** Same prompt class via **NeMo Agent Toolkit** + **NIM**.

Tasks:

1. [x] `make install-nat-demo` — `nvidia-nat[langchain,mcp]==1.7.0` (`react_agent` registered).
2. [x] `configs/pipefy_nat_workflow.yml` — stdio MCP + `nim` + `react_agent`; `include:` is a 2-tool inventory subset of the allowlist.
3. [x] `demos/02_nat_smoke.sh` + `make demo-nat` (`SCENARIO=`).
4. [x] `NVIDIA_API_KEY` in `.env.example`; optional-key warnings in `make doctor`.

**Exit criteria:** [x] `make demo-nat SCENARIO=inventory` completes with `verbose: true` tool iterations visible.

### Phase 4 — Operator experience and reproducibility (day 4) — **shipped**

**Objective:** Anyone can **clone, configure, and run** the full Pipefy → Cursor → NVIDIA story without watching a video.

Tasks:

1. [x] `Makefile` targets: `doctor`, `install-pipefy-tools`, `install-cursor-demo`, `install-nat-demo`, `demo-cursor`, `demo-nat`, `tour` (`scripts/tour.sh`).
2. [x] **[TRY_IT_YOURSELF.md](TRY_IT_YOURSELF.md)** — Steps 0–4 reconciled with shipped targets.
3. [x] `eval/ground_truth.sh` — CLI JSON snapshots (`inventory` implemented; extensible per scenario).
4. [x] `eval/compare.py` + `tests/test_compare.py` — fact check wired into `make tour` for `inventory`.
5. [x] README Quick start → TRY_IT_YOURSELF; docs index in `docs/README.md`.
6. [x] Recording notes in TRY_IT_YOURSELF optional section (no `DEMO_RECORDING.md` — D14).

**Exit criteria:** [x] `make tour` runs Acts 1–3 + `eval/compare.py` `✓`/`✗` on a healthy credentials setup; TRY_IT_YOURSELF Steps 0–4 match Makefile contract.

### Phase 5 — NVIDIA profiler & eval (stretch)

**Status:** Done — runner + profiler + [`docs/BENCHMARKS.md`](BENCHMARKS.md) with dated measured run (2026-06-03).

Tasks:

1. [x] Enable NAT profiler for `nat run` invocation; capture timing JSON (`configs/pipefy_nat_workflow_profile.yml`, `make profile-nat` → gitignored `eval/profiles/`; committed sample `eval/fixtures/example/profile.json`).
2. [x] Golden evaluation set in `eval/golden.yaml` + `eval/golden_loader.py` (`inventory` required; `stale_cards`/`summary` optional — deferred until example fixtures exist).
3. [x] Reliability runner: `eval/run_eval.py` + `make eval` (first-attempt vs with-retries pass rate, median/p90 latency, `8b`/`70b` model override via `--model`).
4. [x] Document results in [`docs/BENCHMARKS.md`](BENCHMARKS.md) (template + reproduce commands); [x] paste dated measured run (operator, 2026-06-03).

**Exit criteria:** [x] Profiler timing JSON captured for one scenario; [x] `eval/golden.yaml` runs against CLI fixtures via `make eval`; [x] [`docs/BENCHMARKS.md`](BENCHMARKS.md) records a dated run.

### Phase 6 — Cursor Cloud agent (stretch)

Tasks:

1. Push repo to GitHub.
2. Cloud agent with `CloudAgentOptions` + `repos=[...]` + MCP stdio in VM.
3. Document `skip_reviewer_request` for quiet CI.

**Exit criteria:** A cloud agent run completes the `inventory` scenario against Pipefy MCP in a Cursor-hosted VM; `agent_id` (`bc-…`) is logged.

### Phase 7 — GPU semantic search (stretch)

See Section 12.

**Exit criteria:** "Find similar cards" returns top-k results over the demo pipe via NIM embeddings + vector index, with a documented CPU fallback.

---

## 15. Hands-on scenarios (reproducible locally)

Scenarios are **not** primarily for screen recording. They are **fixed prompts + Makefile targets** so any operator on a fresh laptop gets the same journey every time.

**Design rules:**

| Rule | Justification |
|------|---------------|
| One command per scenario | Reduces “what flag did they use?” friction for new operators |
| Prompts live in `demos/prompts/*.txt` | Diffable, copy-pasteable, no shell-escaping surprises |
| Same prompt for Cursor and NAT | Proves MCP portability between **Cursor** and **NVIDIA** harnesses |
| Document **expected signals** (not exact prose) | LLM wording varies; facts must match Pipefy CLI |
| Read-only by default | Operators should not need write access to a production org |

**Planned invocation (implementation):**

```bash
make demo-cursor SCENARIO=inventory
make demo-nat    SCENARIO=inventory
```

### Scenario A — Pipe inventory (`inventory`)

**Prompt file:** `demos/prompts/inventory.txt`  

**Prompt (summary):**  
“List all pipes I have access to in the organization and the number of open cards in each.”

**Proves:** **Pipefy** discovery tools, aggregation, permission model.

**What you should see:**

- CLI: JSON array of pipes (Step 1 in [TRY_IT_YOURSELF.md](TRY_IT_YOURSELF.md)).
- Cursor / NAT: at least one `tool_call` to a list/discovery tool; answer mentions pipe names that appear in CLI output.

**CLI ground truth:** `eval/ground_truth.sh inventory`

### Scenario B — Stale cards (`stale_cards`)

**Prompt file:** `demos/prompts/stale_cards.txt`  

**Env:** `DEMO_PIPE_ID`, `DEMO_PHASE_NAME` (phase name as shown in Pipefy UI).

**Prompt (summary):**  
“In pipe `{DEMO_PIPE_ID}`, find cards in phase ‘{DEMO_PHASE_NAME}’ that have been in that phase for more than 7 days.”

**Proves:** Date/filter reasoning—real **Pipefy** ops value.

**Safety:** Read-only.

**What you should see:** Card IDs or titles that exist in `pipefy card list` JSON for that phase; agent cites MCP tools in stream/logs.

### Scenario C — Executive summary (`summary`)

**Prompt file:** `demos/prompts/summary.txt`  

**Prompt (summary):**  
“Summarize the five most recently created open cards in pipe `{DEMO_PIPE_ID}`, including title, current phase, and assignees.”

**Proves:** Sorting, field extraction, synthesis—typical “manager view” on **Pipefy** work.

### Scenario D — Safe write (`move_card`, optional)

**Prompt file:** `demos/prompts/move_card.txt`  

**Requires:** `DEMO_ALLOW_WRITES=true`, dedicated `DEMO_CARD_ID`, sandbox pipe only.

**Proves:** Mutating tools with guardrails—not part of the default `make tour`.

### Scenario ↔ implementation matrix

| SCENARIO | `demo-cursor` | `demo-nat` | In default `make tour` |
|----------|---------------|------------|-------------------------|
| `inventory` | Yes | Yes | Yes |
| `stale_cards` | Yes | Yes | Optional flag |
| `summary` | Yes | Yes | Optional flag |
| `move_card` | Gated | Gated | No |

---

## 16. Operator experience: explained, reproducible, not video-first

### 16.1 Decision

The primary validation path is **“clone and run”**, documented in **[TRY_IT_YOURSELF.md](TRY_IT_YOURSELF.md)**. Video/asciinema is **optional** for users who cannot provision Pipefy credentials.

### 16.2 Justification

| Concern | How this repo addresses it |
|---------|----------------------------|
| “Does it actually work?” | `make doctor` preflight + CLI ground truth before any LLM |
| “Is the NVIDIA path real?” | `nat run` with visible tool iterations and NIM in config |
| “Is Cursor integration concrete?” | `cursor-sdk` script with MCP stdio and logged `run.id` |
| “Is Pipefy integration shallow?” | Real GraphQL via pipefy-mcp-server; ops-style prompts |
| “I have 15 minutes” | TRY_IT_YOURSELF **Suggested path** section |

### 16.3 The “three-act” narrative (guided structure)

Act names are intentional—operators follow a story, not a pile of scripts.

| Act | Name | Technology | Operator action |
|-----|------|------------|-----------------|
| **1** | “See the data” | **Pipefy** + `pipefy` CLI | `pipefy pipe list --json` |
| **2** | “Let Cursor drive” | **Cursor SDK** + Pipefy MCP | `make demo-cursor` |
| **3** | “Let NVIDIA drive” | **NAT** + **NIM** + Pipefy MCP | `make demo-nat` |
| **Encore** | “Same bridge” | MCP | `make tour` compares facts |

This structure makes the **shared MCP layer** obvious: Acts 2 and 3 differ only in harness and LLM provider; **Pipefy** tools stay constant.

### 16.4 Makefile contract (implementation target)

| Target | Purpose |
|--------|---------|
| `make help` | Lists acts and scenarios |
| `make doctor` | Preflight: binaries, env vars, read-only Pipefy ping |
| `make install-pipefy-tools` | Install pipefy/ai-toolkit (`install.sh` or `uv tool install`) @ pinned tag |
| `make install-cursor-demo` | `uv pip install cursor-sdk==0.1.6 python-dotenv` (as built) |
| `make install-nat-demo` | `uv pip install "nvidia-nat[langchain,mcp]==1.7.0"` (as built) |
| `make demo-cursor [SCENARIO=inventory]` | Cursor SDK + MCP |
| `make demo-nat [SCENARIO=inventory]` | NAT + NIM + MCP |
| `make tour` | Acts 1–3 + `eval/compare.py` |

**Justification:** Operators should never guess install order. One `make tour` after `cp .env.example .env` is the happy path.

**`make doctor` specification (implementation contract):**

`doctor` is a non-interactive preflight. It prints one `✓`/`✗` line per check and exits non-zero if any required check fails.

| Check | Pass condition | Required for |
|-------|----------------|--------------|
| `uv` on PATH | `uv --version` succeeds | all |
| `pipefy` CLI on PATH | `pipefy --version` succeeds | all |
| `pipefy-mcp-server` on PATH | binary resolves | all |
| Pipefy env vars | `PIPEFY_SERVICE_ACCOUNT_CLIENT_ID` and `PIPEFY_SERVICE_ACCOUNT_CLIENT_SECRET` set | all |
| Demo pipe vars | `DEMO_PIPE_ID` set (and `DEMO_ORG_ID` for org-wide `inventory`) | all |
| Cursor key | `CURSOR_API_KEY` set | `demo-cursor` |
| NVIDIA key | `NVIDIA_API_KEY` set | `demo-nat` |
| Read-only Pipefy ping | `pipefy pipe list --json` returns a non-empty array | all |

Output rules: never echo secret values (print `set`/`missing` only); exit `0` only when every required check passes; group optional-per-harness checks so an operator running only one harness is not blocked by the other's missing key (warn, do not fail).

**Naming rule:** Use `demo-cursor` and `demo-nat` consistently. Do **not** introduce a separate `nat-demo` target (see [OPEN_DECISIONS.md](OPEN_DECISIONS.md) D11).

### 16.5 Console output guidelines (implementation)

Demos should print **short, labeled sections** so output is scannable in a terminal share:

```
=== Act 1: Pipefy CLI (ground truth) ===
...

=== Act 2: Cursor SDK → Pipefy MCP ===
agent_id: agent-...
run_id: ...
[tool] list_cards: completed
...

=== Act 3: NVIDIA NAT + NIM → Pipefy MCP ===
...
```

Avoid raw JSON dumps unless `VERBOSE=1` is set.

**`make tour` (`scripts/tour.sh`):**

| Step | Behavior |
|------|----------|
| Preflight | Requires Pipefy service account + `DEMO_ORG_ID`, plus `CURSOR_API_KEY` and `NVIDIA_API_KEY` (no secret values printed). |
| Act 1 | `eval/ground_truth.sh inventory` → `eval/fixtures/live/inventory.json`; one-line summary of **listed** pipes. |
| Act 2 | `demos/01_cursor_pipefy_ops.py` stdout → temp file; **one retry** on non-zero exit. |
| Act 3 | `demos/02_nat_smoke.sh` with **`2>&1`** capture; `scripts/extract_nat_answer.py` on the log; up to **3** attempts, each gated by `eval/compare.py` on the extracted answer (not only exit code). |
| Encore | `eval/compare.py` on Cursor and NAT answers vs baseline (count + pipe-name substrings). |
| Exit | `0` only if all steps pass; `TOUR_KEEP_TMP=1` preserves temp answer paths for debugging. |

**Reliability contract (D19):** **Act 2 (Cursor)** is the guaranteed-green path; **Act 3 (NAT, 8b)** is **best-effort** — first-attempt ~3/5 with 8b, made dependable via compare-gated retries. `70b` is an opt-in upgrade (`NIM_MODEL=…`) where the operator's NVIDIA tier allows (D18). First-attempt NAT reliability is a **measured objective in PRD-2** (profiler + golden eval), not something we over-tune the prompt for here.

**Encore / baseline alignment:** When CLI JSON has `pipes_truncated: true` (or `pipesCount > len(pipes[])`), `eval/compare.py` fact-checks the **visible page**, not org-wide `pipesCount`. Agent answers that mention both “5 pipes” and “274 total” should match the listed count. Operational detail: [LEARNINGS.md](LEARNINGS.md).

**NAT + 8b:** Default `meta/llama-3.1-8b-instruct` is demo-capable but may need multiple tour attempts (wrong tool args, recursion limit, incomplete `Final Answer`). Upgrade path: `meta/llama-3.1-70b-instruct` in workflow YAML when the operator’s NIM tier allows ([OPEN_DECISIONS.md](OPEN_DECISIONS.md) D18).

### 16.6 What we do not require

- Provision a GPU (core tour).
- Click through Pipefy UI during the demo (CLI/MCP only).
- Watch a 10-minute video before running commands.
- Enable write scenarios unless they opt in.

---

## 17. Evaluation strategy

### 17.1 Philosophy

Agents are **non-deterministic**; evaluation should target **verifiable facts** about Pipefy entities, not prose quality alone.

### 17.2 MVP eval (shipped — Phase 4)

1. **CLI snapshot** — `eval/ground_truth.sh` writes `eval/fixtures/live/<scenario>.json` (gitignored); `eval/fixtures/example/` holds synthetic samples (D13).
2. **Extraction** — `eval/compare.py` reads `pipe_count` and `pipe_names` from CLI JSON and agent answer text.
3. **Pass rule** — **Count match + pipe-name substring** in agent answer (D12); truncation-aware baseline (listed pipes when `pipes_truncated`); wired in `make tour` for `inventory` only. Act 3 may retry NAT up to three times with an inline compare gate before Encore (§16.5).

### 17.3 NAT-native eval (Phase 5)

Shipped artifacts (PRD-2):

1. **Golden set** — `eval/golden.yaml` + `eval/golden_loader.py`; `inventory` scenario required (`stale_cards`/`summary` optional when fixtures land).
2. **Runner** — `eval/run_eval.py` + `make eval`; scores via `eval/compare.py` and `scripts/extract_nat_answer.py`; reports first-attempt vs with-retries pass rate and median/p90 latency per harness (`cursor`|`nat`|`both`).
3. **Profiler** — `configs/pipefy_nat_workflow_profile.yml`, `make profile-nat` → gitignored `eval/profiles/`; sample shape in `eval/fixtures/example/profile.json`.
4. **Benchmarks report** — [`docs/BENCHMARKS.md`](BENCHMARKS.md) (reproduce commands + dated measured table, 2026-06-03).

Use NeMo Agent Toolkit **evaluation system** (per NAT docs) with golden Q&A pairs referencing CLI fixtures.

**Justification:** Demonstrates NVIDIA toolkit beyond `nat run`—important for “production agent ops” narrative.

### 17.4 Cursor-specific eval

Log `run.conversation()` to `eval/transcripts/` for manual review; optional hook to fail CI if no tool_call occurred (agent hallucinated without Pipefy access).

---

## 18. Operational concerns

### 18.1 Rate limits and latency

Pipefy GraphQL may rate-limit aggressive agents. Mitigations:

- Narrow tool `include` list.
- Set `max_iterations` to match the inventory tool budget (shipped: **22** → `recursion_limit` 46; see D10 / [LEARNINGS.md](LEARNINGS.md)). Avoid unbounded loops on large orgs.
- Cache pipe schema in prompt context (future).

### 18.2 Cost

| Surface | Cost driver |
|---------|-------------|
| Cursor SDK | Cursor usage dashboard (SDK tag) |
| NIM | NVIDIA API usage |
| Pipefy | Normal API usage |

Document that demos should use **small card sets**.

### 18.3 Version pinning

Pin the `pipefy/ai-toolkit` release tag in README. NAT and `cursor-sdk` use minimum versions tested in CI (add `.github/workflows/ci.yml` when scripts exist).

---

## 19. Risks and mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| MCP tool rename in pipefy/ai-toolkit | NAT `include` breaks | Pin version; CI smoke list tools |
| Service account lacks pipe access | Empty results | Pre-flight `pipefy pipe list` in Makefile |
| Cursor API key missing | Demo 01 fails | Clear error message; document dashboard URL |
| NVIDIA_API_KEY missing | NAT path fails | Document `NVIDIA_API_KEY` in `.env.example` and `make doctor` |
| Agent hallucinates without tools | False success | Assert tool_call in transcript |
| Accidental production pipe mutation | Data incident | `DEMO_ALLOW_WRITES`; sandbox org |
| 149-tool overload | Poor agent quality | `tool_allowlist.yml` |

---

## 20. Task breakdown hints (for issue tracking)

Copy each block into GitHub Issues / Linear / Jira as needed.

### Epic: Tooling baseline (Pipefy)

- [ ] P0-1: Document install of pipefy/ai-toolkit (`pipefy-mcp-server` + `pipefy` CLI) @ version X
- [ ] P0-2: Service account setup checklist (Pipefy Admin)
- [ ] P0-3: MCP Inspector connection screenshot/log
- [ ] P0-4: Generate `configs/tool_allowlist.yml`

### Epic: Cursor SDK integration

- [ ] C-1: Add `demos/01_cursor_pipefy_ops.py` skeleton
- [ ] C-2: Wire `StdioMcpServerConfig` for `pipefy-mcp-server`
- [ ] C-3: Implement Scenario A prompt
- [ ] C-4: Error handling and exit codes
- [ ] C-5: Optional streaming output for recordings

### Epic: NVIDIA NAT integration

- [ ] N-1: Add `configs/pipefy_nat_workflow.yml`
- [ ] N-2: `make demo-nat` target
- [ ] N-3: Scenario A parity with Cursor demo
- [ ] N-4: Document NIM model selection and API key
- [x] N-5: Profiler artifact (stretch) — `make profile-nat`, `eval/fixtures/example/profile.json`

### Epic: Operator experience (reproducible tour)

- [ ] R-1: Author and keep in sync `docs/TRY_IT_YOURSELF.md`
- [ ] R-2: `Makefile` with `doctor`, `tour`, `demo-cursor`, `demo-nat` (no `nat-demo` alias)
- [ ] R-3: Labeled console sections in demo scripts
- [ ] R-4: README Quick start → docs index → TRY_IT_YOURSELF

### Epic: Evaluation & ground truth

- [ ] E-1: `eval/ground_truth.sh`
- [ ] E-2: `eval/compare.py` for Scenario A (wired into `make tour`)
- [ ] E-3: *(Optional, low priority)* Recording notes inside TRY_IT_YOURSELF; no separate `DEMO_RECORDING.md` (D14)
- [x] E-4: `eval/golden.yaml` + `eval/golden_loader.py` + `eval/run_eval.py` + `make eval` (Phase 5)
- [x] E-5: `docs/BENCHMARKS.md` (template + dated measured reliability table, 2026-06-03)

### Epic: Optional GPU semantics

- [ ] G-1: Spike NIM embeddings on 100 cards
- [ ] G-2: FAISS/cuVS index CLI
- [ ] G-3: Agent prompt “find similar cards”

---

## 21. References

### Pipefy

- [pipefy/ai-toolkit (GitHub)](https://github.com/pipefy/ai-toolkit) — official Pipefy AI Toolkit: `pipefy-mcp-server`, `pipefy` CLI, `pipefy-sdk`, agent skills
- Pipefy agent skills: `npx skills add pipefy/ai-toolkit` (e.g. `pipefy-pipes-and-cards`)
- Pipefy GraphQL API (via `pipefy-sdk` in the upstream repo)
- CLI/MCP parity: `docs/parity.md`; auth precedence: `packages/cli/README.md` (both in pipefy/ai-toolkit)

### Cursor

- [Cursor Python SDK](https://cursor.com/docs/sdk/python)
- [Cursor MCP documentation](https://cursor.com/docs/mcp)
- [Cloud Agents API](https://cursor.com/docs/cloud-agent/api/endpoints) (stretch goals)

### NVIDIA

- [NeMo Agent Toolkit — source repository (GitHub)](https://github.com/NVIDIA/NeMo-Agent-Toolkit) — `nvidia-nat` package, `nat` CLI, `examples/`, Apache-2.0; primary upstream consulted for this plan
- [NeMo Agent Toolkit — Overview](https://docs.nvidia.com/nemo/agent-toolkit/latest/index.html)
- [NeMo Agent Toolkit — MCP Client](https://docs.nvidia.com/nemo/agent-toolkit/latest/build-workflows/mcp-client.html)
- [NeMo Agent Toolkit — MCP Workflows Index](https://docs.nvidia.com/nemo/agent-toolkit/latest/workflows/mcp/index.html)
- [CUDA-X Libraries](https://developer.nvidia.com/cuda/cuda-x-libraries)
- [NVIDIA Build (API keys / NIM)](https://build.nvidia.com/)
- [NVIDIA Agent Skills catalog](https://github.com/NVIDIA/skills) — optional, install per skill via the official CLI; **do not vendor** skill folders into this repo (they are mirrored from product repos under their own licenses). The catalog itself lists **no NeMo Agent Toolkit (NAT) skill**, but NAT ships its own **AI Coding Agent Skill** in the [source repo](https://github.com/NVIDIA/NeMo-Agent-Toolkit) for agent-assisted workflow building/eval/observability — the most on-topic skill for this project. Other tangential catalog skills apply only to stretch phases:
  - Phase 5 (eval/profiler): `rag-eval`, `rag-perf` — `npx skills add nvidia/skills --skill rag-eval --agent cursor`
  - Phase 7 (GPU semantic search): `nemo-retriever` — `npx skills add nvidia/skills --skill nemo-retriever --agent cursor`

### Protocol

- [Model Context Protocol](https://modelcontextprotocol.io/) — shared tool contract between Pipefy, Cursor, and NVIDIA harnesses

---

## Document history

| Version | Date | Notes |
|---------|------|-------|
| 0.1 | 2026-06-02 | Initial architecture and implementation plan |
| 0.2 | 2026-06-02 | Reproducible tour (TRY_IT_YOURSELF); docs index; OPEN_DECISIONS; private CONTEXT |
| 0.3 | 2026-06-02 | Consistency audit; docs index; OPEN_DECISIONS; private CONTEXT; Makefile naming aligned |
| 0.4 | 2026-06-02 | Audit fixes: phase-number normalization, §18 renumber, `make doctor` spec, layout sync (eval/fixtures, eval/transcripts), `.env` write vars; D1–D14 resolved (License MIT; no separate `DEMO_RECORDING.md`) |
| 0.5 | 2026-06-02 | Pipefy toolkit migrated to official `pipefy/ai-toolkit` (URLs, framing, install, registry/parity/config paths, 149 tools across ten domains); NAT source repo referenced |
| 0.6 | 2026-06-02 | MVP close-out: §2.3 and §14 Phases 0–4 marked shipped; pinned `v0.2.0-beta.2`, 12-tool allowlist, NIM `meta/llama-3.1-8b-instruct` recorded |

---

*This plan intentionally showcases complementary expertise: **Pipefy** domain operations via a community MCP toolkit, **Cursor** programmatic agent harness patterns, and **NVIDIA NeMo Agent Toolkit** with **NIM** for measured, production-oriented agent workflows—all unified by **MCP**.*
