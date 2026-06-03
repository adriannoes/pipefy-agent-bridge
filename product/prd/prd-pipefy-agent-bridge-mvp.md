# PRD: Pipefy Agent Bridge — Reproducible MVP Tour

**Status:** Shipped (MVP delivered 2026-06-02; see [product/prd/README.md](README.md) scope deltas and [docs/LEARNINGS.md](../../docs/LEARNINGS.md))
**Version:** 0.2
**Date:** 2026-06-02
**Owner:** Repository maintainer (this repo is hosted under the maintainer's own account)
**Related documents:**
- [docs/ARCHITECTURE_AND_IMPLEMENTATION_PLAN.md](../../docs/ARCHITECTURE_AND_IMPLEMENTATION_PLAN.md) (Phases 0–4, §13 layout, §15 scenarios, §16 operator UX, §17 eval)
- [docs/TRY_IT_YOURSELF.md](../../docs/TRY_IT_YOURSELF.md) (runbook spec)
- [docs/OPEN_DECISIONS.md](../../docs/OPEN_DECISIONS.md) (D1–D14 resolved)
- [engineering/tasks/tasks-prd-pipefy-agent-bridge-mvp.md](../../engineering/tasks/tasks-prd-pipefy-agent-bridge-mvp.md) (task list / execution plan)

> Scope note: this PRD covers the **MVP vertical slice only** (architecture Phases 0–4). Profiler/eval depth (Phase 5), Cursor Cloud (Phase 6), and GPU semantic search (Phase 7) are tracked as separate stretch PRDs.

---

## 1. Introduction / Overview

`pipefy-agent-bridge` is a public reference repository that shows how to operate **Pipefy** through AI agents using a single **Model Context Protocol (MCP)** tool contract, driven by two complementary harnesses: the **Cursor Python SDK** and the **NVIDIA NeMo Agent Toolkit (NAT)** with **NIM**. Pipefy access is delegated entirely to the **official Pipefy AI Toolkit** ([`pipefy/ai-toolkit`](https://github.com/pipefy/ai-toolkit)), which ships the `pipefy-mcp-server` binary, the `pipefy` CLI, the `pipefy-sdk`, and agent skills; this repo only orchestrates and validates.

Today the repository is documentation-only: the runbook, architecture, and decisions exist, but no runtime artifacts (Makefile, demo scripts, NAT workflow, eval) are built yet. This PRD defines the **first shippable slice**: a fresh clone can run `make doctor` → `make demo-cursor` → `make demo-nat` → `make tour` for the `inventory` scenario and see the same Pipefy facts surfaced three ways (CLI ground truth, Cursor agent, NAT agent), with a lightweight automated fact check.

**Goal:** an operator with credentials completes [TRY_IT_YOURSELF.md](../../docs/TRY_IT_YOURSELF.md) Steps 0–4 on a clean macOS/Linux machine in ~20–30 minutes without guessing.

---

## 2. Goals

1. Provide a one-command preflight (`make doctor`) that verifies tooling, env vars, and read-only Pipefy access before any LLM runs.
2. Run the `inventory` scenario end-to-end through **both** harnesses (Cursor SDK and NAT + NIM) against the **same** `pipefy-mcp-server` over MCP stdio.
3. Establish deterministic **ground truth** via the `pipefy` CLI and compare it to agent output with a simple, non-flaky fact check.
4. Make the tour reproducible from a fresh clone using a documented Makefile happy path, with no video required.
5. Keep the agent tool surface curated (8–15 MCP tools) to avoid tool sprawl.
6. Keep the repository public-safe: no secrets committed, MIT licensed, sandbox-scoped credentials.

---

## 3. User Stories

- **As an operator new to the repo**, I want to copy `.env.example`, fill in credentials, and run `make doctor`, so that I know my environment is correct before spending LLM calls.
- **As a developer evaluating the Cursor SDK**, I want to run `make demo-cursor SCENARIO=inventory` and see logged `agent_id`/`run.id` plus tool calls against Pipefy MCP, so that I can confirm the agent used real tools.
- **As an ML/agent engineer evaluating NVIDIA NAT**, I want to run `make demo-nat SCENARIO=inventory` and see NAT discover MCP tools and answer via NIM, so that I can confirm the same MCP contract works under a YAML workflow.
- **As a reviewer of the repo**, I want `make tour` to show the CLI baseline next to both agent answers with a `✓`/`✗` fact check, so that I can trust the agents are not hallucinating.
- **As a security-conscious maintainer**, I want write operations gated and credentials sandbox-scoped, so that running the demo cannot mutate production data.

---

## 4. Functional Requirements

Requirements are grouped by area and map to architecture epics (P0 / C / N / R / E).

### 4.1 Preflight and Pipefy tool chain (P0)
1. The repo MUST provide `make install-pipefy-tools` that installs `pipefy-mcp-server` and the `pipefy` CLI from [`pipefy/ai-toolkit`](https://github.com/pipefy/ai-toolkit) at an **explicit pinned version tag** (D2). Use the official `install.sh` (`--client cursor`) or `uv tool install` with the pre-1.0 workspace-member flags (`pipefy-sdk`, `pipefy-auth` via `#subdirectory=packages/...`); pin a tag (e.g. `@v0.2.0-beta.2`), never `@latest`.
2. The repo MUST provide `make doctor` implementing the check contract in [ARCHITECTURE §16.4](../../docs/ARCHITECTURE_AND_IMPLEMENTATION_PLAN.md#164-makefile-contract-implementation-target): verify `uv`, `pipefy`, `pipefy-mcp-server`, required env vars (printed as `set`/`missing`, never values), and a read-only `pipefy pipe list --json`. It MUST exit non-zero if any required check fails.
3. The repo MUST provide `configs/tool_allowlist.yml` with a curated MVP list of 8–15 MCP tool names (introspection + read; `inventory` needs at least pipe-list/pipe-get/card-list), frozen from `nat mcp client tool list` or MCP Inspector against the pinned server version (D4). **As built:** the repo-contract allowlist is **12 tools**; the NAT workflow intentionally consumes a **narrower subset** (see FR-10) because the 8b model degrades with a wide tool surface (see [docs/LEARNINGS.md](../../docs/LEARNINGS.md)).
4. `make doctor` MUST NOT print secret values.

### 4.2 Cursor SDK harness (C)
5. The repo MUST provide `demos/01_cursor_pipefy_ops.py` that loads `.env` (`python-dotenv`), creates an agent with `Agent.create(...)` using explicit `local=LocalAgentOptions(cwd=...)`, `model="composer-2.5"`, and an inline `StdioMcpServerConfig(command="pipefy-mcp-server", env=...)` for the `pipefy` MCP server.
6. The script MUST send a fixed prompt loaded from `demos/prompts/inventory.txt`, wait for the run, and print the final answer.
7. The script MUST log `agent.agent_id` and `run.id`.
8. The script MUST distinguish startup failure (`CursorAgentError`, exit code 1) from run failure (`result.status == "error"`, exit code 2), and exit 0 on success.
9. `make demo-cursor [SCENARIO=inventory]` MUST run the script with the selected scenario prompt (default `inventory`).

### 4.3 NVIDIA NAT harness (N)
10. The repo MUST provide `configs/pipefy_nat_workflow.yml` defining: an `llms` block with `_type: nim` (model `meta/llama-3.1-8b-instruct`, D9); a `function_groups.pipefy` block with `_type: mcp_client`, `server.transport: stdio`, `server.command: pipefy-mcp-server`, `server.env`, and an `include:` list (inventory subset of `configs/tool_allowlist.yml`; shipped: `search_pipes`, `get_cards`); and a `workflow` block with `_type: react_agent`, `tool_names: [pipefy]`, `llm_name` pointing at the NIM LLM, `max_iterations` per D10 (shipped: **22**), and `verbose: true`.
11. The repo MUST provide `demos/02_nat_smoke.sh` (and/or the Makefile target) that runs `nat run --config_file configs/pipefy_nat_workflow.yml --input "<inventory prompt>"`.
12. `make demo-nat [SCENARIO=inventory]` MUST run the same scenario prompt as the Cursor harness (default `inventory`).
13. The NAT path MUST require only `NVIDIA_API_KEY` + Pipefy credentials (no Cursor key).

### 4.4 Scenarios and prompts (C/N)
14. The repo MUST provide three prompt files: `demos/prompts/inventory.txt`, `demos/prompts/stale_cards.txt`, `demos/prompts/summary.txt`. The same prompt file MUST be used by both harnesses for a given scenario.
15. `inventory` is the **only gated scenario** for this PRD; `stale_cards` and `summary` are best-effort (prompts created and runnable via `SCENARIO=`, but not part of the acceptance gate).
16. The default tour and all default targets MUST be **read-only**; the `move_card` write scenario is out of scope (see Non-Goals).

### 4.5 Tour and operator experience (R)
17. The repo MUST provide `make help` listing the acts/targets and `make tour` that: prints the three labeled layers (CLI / Cursor / NAT), runs the Step 1 CLI baseline, runs `demo-cursor` and `demo-nat` with the same `inventory` prompt, and prints `✓`/`✗` from the eval check.
18. Demo output MUST use short labeled sections (per [ARCHITECTURE §16.5](../../docs/ARCHITECTURE_AND_IMPLEMENTATION_PLAN.md)) and avoid raw JSON dumps unless a verbose flag is set.
19. [TRY_IT_YOURSELF.md](../../docs/TRY_IT_YOURSELF.md) MUST be updated so every command in Steps 0–4 works as written.

### 4.6 Evaluation (E)
20. The repo MUST provide `eval/ground_truth.sh inventory` that snapshots the CLI JSON baseline for the `inventory` scenario.
21. The repo MUST provide `eval/compare.py` that extracts key facts (e.g., pipe count and pipe-name substrings) from the CLI baseline and from agent output, and prints pass/fail using **count + pipe-name substring matching** (D12), not exact-ID matching.
22. `make tour` MUST wire `eval/compare.py` for the `inventory` scenario and surface its `✓`/`✗` result.
23. Eval fixtures MUST follow D13: `eval/fixtures/example/` committed (synthetic), `eval/fixtures/live/` gitignored.

### 4.7 Repository, CI, and licensing
24. The repo MUST include a top-level `LICENSE` (MIT, D1) — already present.
25. The repo MUST include a minimal CI workflow (`.github/workflows/ci.yml`) running **lint/format only** (`ruff`), with **no external network calls** (no Pipefy/NIM/Cursor calls in CI).
26. An **initial git commit** of the scaffolding MUST be created as a deliverable; pushing/publishing to a remote is out of scope for this PRD.
27. `.env.example` MUST remain the single source of required variables; no secret values anywhere in the repo.

### 4.8 Planning hygiene (close-out)
28. At the **end of development**, the three lightweight planning artifacts MUST be reconciled with what was actually built, so the planning stays connected and trustworthy for the stretch PRDs:
    - [docs/ARCHITECTURE_AND_IMPLEMENTATION_PLAN.md](../../docs/ARCHITECTURE_AND_IMPLEMENTATION_PLAN.md) §14 — mark Phase 0–4 boxes/exit criteria; record the frozen `pipefy/ai-toolkit` version and observed tool count (the backbone).
    - [product/prd/README.md](README.md) — update PRD-1 status (Draft → Done) and the roadmap (the living index).
    - [docs/OPEN_DECISIONS.md](../../docs/OPEN_DECISIONS.md) — move any decision settled during the build to **Resolved** with date (cross-cutting decision log).

---

## 5. Non-Goals (Out of Scope)

1. **Write/mutation scenarios** (`move_card`): gated behind `DEMO_ALLOW_WRITES=true`; not built or accepted in this PRD.
2. **NAT profiler and NAT-native evaluation** (Phase 5).
3. **Cursor Cloud agents** (Phase 6) and pushing the repo to a remote.
4. **GPU embeddings / semantic search** (Phase 7) and any GPU requirement.
5. **Reimplementing Pipefy GraphQL** in this repo — all Pipefy access stays in `pipefy-mcp-server`.
6. **A unified Cursor+NAT abstraction layer** — two separate entrypoints by design.
7. **Exact-ID eval matching**, golden datasets, or LLM-judge scoring.
8. **Windows-native support** (WSL2 is acceptable; macOS/Linux are the tested path).
9. **Acceptance gating of `stale_cards` / `summary`** — created and runnable, but not required for "done".

---

## 6. Design Considerations

- **Console UX:** labeled "three-act" sections (Act 1 CLI / Act 2 Cursor / Act 3 NAT / Encore tour) so a terminal share is self-explanatory; keep wording aligned with the README "Act" narrative and TRY_IT "Step" mapping.
- **No UI:** this is a CLI/terminal experience; no web frontend.
- **Determinism vs. probabilism:** the CLI baseline is the trusted layer; agent answers are compared to it, never the reverse.

---

## 7. Technical Considerations

- **Stack:** Python 3.11+ (matches `pipefy-mcp-server`); `uv` for env/install (D7); `python-dotenv` for `.env` (D8); `ruff` for lint; GNU Make as the task runner.
- **Upstream contracts (verified against docs):**
  - Cursor SDK: `Agent.create`, `LocalAgentOptions`, `StdioMcpServerConfig`, `Agent.prompt`, `CursorAgentError`, `Cursor.models.list()`; inline MCP is not persisted across `Agent.resume()`.
  - NAT: `function_groups._type: mcp_client` + `server.transport: stdio` + `include:`; `workflow._type: react_agent` with `tool_names` + `llm_name`; `_type: nim`. Source: [NVIDIA/NeMo-Agent-Toolkit](https://github.com/NVIDIA/NeMo-Agent-Toolkit).
- **Dependencies / critical path:** `install-pipefy-tools` → freeze `tool_allowlist.yml` (gates NAT `include:`) → `demo-cursor inventory` → `demo-nat inventory` → `make tour` + `eval/compare.py`.
- **Security:** service-account auth injected into MCP stdio `env`; sandbox pipe with minimum scope; writes gated; secrets only in gitignored `.env`. Recommend rotating any credentials that have been shared outside the repo.
- **Upstream (Pipefy):** the toolkit moved to the **official** [`pipefy/ai-toolkit`](https://github.com/pipefy/ai-toolkit) `uv` workspace (packages `pipefy-sdk`, `pipefy-mcp-server`, `pipefy-cli`, `pipefy-auth` + `skills/`). Binary/CLI names are unchanged (`pipefy-mcp-server`, `pipefy`). The MCP server exposes **149 tools across ten domains**; canonical names live in `PIPEFY_TOOL_NAMES` (`packages/mcp/src/pipefy_mcp/tools/registry.py`). CLI/MCP parity: `docs/parity.md`; auth precedence: `packages/cli/README.md`.
- **Version pinning:** pin the `pipefy/ai-toolkit` tag in README + Makefile (D2); record the exact tool count observed on that pinned version.
- **NIM model tier (D9):** default `meta/llama-3.1-8b-instruct` (sufficient for `inventory`). A `70b` upgrade path is documented for harder prompts (e.g. `stale_cards` date reasoning) **pending confirmation that the maintainer's `NVIDIA_API_KEY` tier grants `70b` access** — keep the workflow YAML model name as a single, easily swapped value to support both options.

---

## 8. Success Metrics

1. A clean clone with valid credentials completes TRY_IT_YOURSELF Steps 0–4 in ~20–30 minutes (acceptance: a colleague who did not author the repo succeeds without assistance).
2. `make doctor` exits 0 with all required checks `✓` on a correctly configured machine and non-zero (with a clear failing line) when a required var/binary is missing.
3. `make demo-cursor SCENARIO=inventory` and `make demo-nat SCENARIO=inventory` both produce an answer naming pipes that appear in the CLI baseline, with at least one tool call observed in logs/stream.
4. `make tour` prints `✓` for the `inventory` fact check on a healthy run.
5. CI passes `ruff` on the repo with no external calls.

---

## 9. Resolved Clarifications

1. **Cursor key — RESOLVED:** the demo uses a **Cursor user key**, already present in the local `.env` (`CURSOR_API_KEY`). No service-account key needed for the local tour.
2. **Exact MCP tool names — RESOLVED (freeze in implementation):** allowlist names will be frozen against the pinned [`pipefy/ai-toolkit`](https://github.com/pipefy/ai-toolkit) version, read from `PIPEFY_TOOL_NAMES` (`packages/mcp/src/pipefy_mcp/tools/registry.py`). Note: the Pipefy toolkit moved to this **official** repo — all references updated.
3. **`70b` NIM option — MAPPED (one item still open):** keep `8b` as default and `70b` documented as an upgrade path; **still to confirm** whether the maintainer's `NVIDIA_API_KEY` tier grants `70b` access. Both options are kept available via a single model-name value in the workflow YAML.
4. **Owner/maintainer — RESOLVED:** not separately documented; this repo lives under the maintainer's own account/repo, so ownership is implicit. `LICENSE` copyright holder stays "pipefy-agent-bridge contributors".

**Remaining open before sign-off:** only item 3's `70b` key-tier check (does not block the `inventory` gate).

---

## 10. Acceptance Criteria (definition of done)

- [ ] `LICENSE` (MIT) present and referenced from README.
- [ ] `make help`, `make doctor`, `make install-pipefy-tools`, `make install-cursor-demo`, `make install-nat-demo`, `make demo-cursor`, `make demo-nat`, `make tour` exist and are documented.
- [ ] `make doctor` enforces the §16.4 check contract (pass/fail, no secret values, non-zero on failure).
- [ ] `configs/tool_allowlist.yml` frozen (8–15 tools) against the pinned `pipefy/ai-toolkit` version.
- [ ] `demos/01_cursor_pipefy_ops.py` answers `inventory`, logs `agent_id`/`run.id`, and uses the documented exit codes.
- [ ] `configs/pipefy_nat_workflow.yml` + `make demo-nat` answer `inventory` via NIM with visible tool discovery.
- [ ] Both harnesses answer `inventory` consistently with the CLI baseline (gate).
- [ ] `demos/prompts/{inventory,stale_cards,summary}.txt` exist; `inventory` is the gated scenario.
- [ ] `eval/ground_truth.sh inventory` + `eval/compare.py` produce a `✓` for `inventory`, wired into `make tour`.
- [ ] `eval/fixtures/example/` committed; `eval/fixtures/live/` gitignored.
- [ ] `.github/workflows/ci.yml` runs `ruff` only (no external calls) and passes.
- [ ] TRY_IT_YOURSELF Steps 0–4 are fully runnable as written.
- [ ] Initial git commit created (no remote push required).
- [ ] Close-out: ARCHITECTURE §14, `product/prd/README.md`, and `docs/OPEN_DECISIONS.md` reconciled with what was built (FR-28).
