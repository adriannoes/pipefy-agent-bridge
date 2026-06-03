# Tasks — Pipefy Agent Bridge MVP

**PRD:** [product/prd/prd-pipefy-agent-bridge-mvp.md](../../product/prd/prd-pipefy-agent-bridge-mvp.md)
**Architecture:** [docs/ARCHITECTURE_AND_IMPLEMENTATION_PLAN.md](../../docs/ARCHITECTURE_AND_IMPLEMENTATION_PLAN.md) (Phases 0–4)
**Roadmap:** [product/prd/README.md](../../product/prd/README.md)

> Sprint mapping (thin vertical slice first): **Sprint 0** = tasks 1–2 · **Sprint 1** = tasks 3–4 · **Sprint 2** = task 5 · **Close-out** = task 6.
> Critical path: **1.0 → 2.0 → (3.0 ∥ 4.0) → 5.0 → 6.0**. Execute one sub-task at a time (see [.cursor/commands/development.md](../../.cursor/commands/development.md)).

## Relevant Files

- `LICENSE` — MIT license (verified; README links via [MIT](LICENSE)).
- `pyproject.toml` — `ruff` config + dev deps; project metadata (created).
- `uv.lock` — lockfile from `uv sync --extra dev` (created).
- `Makefile` — `help`, `doctor`, `install-*`, `demo-cursor`, `demo-nat`, `tour`; `install-pipefy-tools` @ pinned tag (2.1); `install-cursor-demo` pins `cursor-sdk==0.1.6` + `python-dotenv==1.2.2` (3.3); `install-nat-demo` pins `nvidia-nat[langchain,mcp]==1.7.0` (4.3); `demo-cursor` / `demo-nat` load `.env` and run harness scripts (3.4 / 4.4); `doctor` loads `.env` and runs `scripts/doctor.sh` (2.3).
- `.github/workflows/ci.yml` — lint-only CI (`ruff`), no external calls (created).
- `scripts/doctor.sh` — preflight: binaries, env (set/missing only), read-only `pipefy pipe list --json` ping (created in task 2.2).
- `configs/tool_allowlist.yml` — 12 read/inventory MCP tool names @ `v0.2.0-beta.2`, verified via `nat mcp client tool list` (created in task 2.4).
- `configs/pipefy_nat_workflow.yml` — NAT `react_agent` + `mcp_client` (stdio) + `nim`; 2-tool inventory subset from `tool_allowlist.yml` (4.1).
- `demos/01_cursor_pipefy_ops.py` — Cursor SDK harness: dotenv, MCP stdio, tool-call stream, exit 0/1/2 (3.2).
- `demos/02_nat_smoke.sh` — NAT wrapper: loads `.env`, scenario prompt, `nat run` with Act 3 header (4.2).
- `demos/prompts/inventory.txt` — org-wide inventory scenario prompt (3.1).
- `demos/prompts/stale_cards.txt` — stale cards in `DEMO_PHASE_NAME` > 7 days in pipe `DEMO_PIPE_ID` (5.1).
- `demos/prompts/summary.txt` — five newest open cards with title/phase/assignees in `DEMO_PIPE_ID` (5.1).
- `eval/ground_truth.sh` — CLI JSON baseline snapshot per scenario (`inventory` → `pipefy pipe list --json` → `eval/fixtures/live/<scenario>.json`; loads `.env` from repo root).
- `eval/compare.py` — count + pipe-name substring fact check (D12); CLI `--baseline` / `--answer`.
- `eval/fixtures/example/inventory.json` — committed synthetic baseline (3 fictional pipes; `live/` gitignored).
- `tests/test_compare.py` — unit tests for `eval/compare.py` fact extraction/matching.
- `docs/TRY_IT_YOURSELF.md` — Steps 0–4 reconciled with shipped Makefile targets, install order, `make tour`/`eval/*`, scenarios; removed “planned” drift (5.6).
- `docs/LEARNINGS.md` — operational learnings: Pipefy truncated `pipesCount`, Cursor/NAT harness limits, Encore/compare, NAT 8b flakiness (post-tour tuning).
- `scripts/tour.sh` — Acts 1–3 + Encore; NAT capture `2>&1`, extract answer, up to 3 demo-nat attempts with compare gate.
- `scripts/extract_nat_answer.py` — extracts last `Workflow Result` / `Final Answer` from noisy `nat run` logs for compare.
- `tests/test_extract_nat_answer.py` — unit test for NAT answer extraction.
- `docs/ARCHITECTURE_AND_IMPLEMENTATION_PLAN.md` — §2.3 + §14 Phases 0–4 shipped; toolkit `v0.2.0-beta.2`, 12-tool allowlist, NIM model recorded (6.1).
- `product/prd/README.md` — PRD-1 status Done; shipped scope-delta table (6.2).
- `docs/OPEN_DECISIONS.md` — D2/D4 build outcomes, D18 (`70b` tier), D20 (dep pins); MVP gates closed (6.3).

### Notes

- Stack: Python 3.11+, `uv`, `python-dotenv`; lint with `ruff`. GNU Make as task runner.
- Upstream Pipefy toolkit: [`pipefy/ai-toolkit`](https://github.com/pipefy/ai-toolkit). Pin a tag (e.g. `@v0.2.0-beta.2`); never `@latest`.
- `eval/compare.py` is the only unit-testable pure logic; test it offline (no network). CI stays lint-only.
- Run tests with `uv run pytest tests/ -v`.
- The same prompt file feeds both harnesses per scenario; `inventory` is the only gated scenario.
- **Operational learnings (2025-06-02):** see [docs/LEARNINGS.md](../../docs/LEARNINGS.md). Highlights:
  - **Pipefy:** `pipe list --json` may set `pipesCount` to org total while `pipes[]` is truncated; fact-check must use listed pipes when `pipes_truncated` is true (fixed in `eval/compare.py`).
  - **Cursor:** `inventory` harness is usually stable; answers may cite org total + visible page — compare handles both.
  - **NVIDIA:** `meta/llama-3.1-8b-instruct` + `react_agent` is **flaky** for multi-tool inventory (recursion limit, wrong `search_pipes` args, incomplete Final Answer); workflow uses a **2-tool NAT subset** (`search_pipes`, `get_cards`), prose `additional_instructions` (no `{json}` in YAML), `use_native_tool_calling`, stderr capture, and tour retries. **`make tour` may need 2–3 NAT attempts** until 70b or workflow hardening lands.
  - **Follow-up (optional):** mark 5.0 acceptance “tour green first run” after NAT stabilization; see LEARNINGS open follow-ups.

## Tasks

- [x] 1.0 **Repository scaffolding, license, Makefile skeleton & lint-only CI** _(Sprint 0)_

  **Trigger:** Start of MVP build on a fresh clone.
  **Enables:** Every later task (Make targets to extend, lint gate, reproducible dev env).
  **Depends on:** Nothing.
  **Acceptance criteria:** `make help` lists all planned targets; `uv run ruff check .` passes; `.github/workflows/ci.yml` runs `ruff` and nothing network-bound; `LICENSE` (MIT) present; `pyproject.toml` is valid (`uv run python -c "import tomllib,1 and open('pyproject.toml','rb') as f"` parses).

  - [x] 1.1 Create `pyproject.toml` with project metadata, Python `>=3.11`, and `ruff` config
    - **File**: `pyproject.toml` (create new)
    - **What**: Minimal `[project]` (name `pipefy-agent-bridge`, version `0.1.0`, requires-python `>=3.11`), an optional `[project.optional-dependencies] dev = ["ruff", "pytest"]`, and a `[tool.ruff]` block (line length 100, target py311).
    - **Why**: Single source for dev deps and lint config; consumed by CI and local `uv run`.
    - **Pattern**: Standard `uv`/PEP 621 layout; mirror the pinning discipline in [ARCHITECTURE §18.3](../../docs/ARCHITECTURE_AND_IMPLEMENTATION_PLAN.md).
    - **Verify**: `uv run ruff --version` works; `uv run python -c "import tomllib; tomllib.load(open('pyproject.toml','rb'))"` exits 0.
  - [x] 1.2 Create `Makefile` skeleton with `help` and stubbed targets
    - **File**: `Makefile` (create new)
    - **What**: Define `help` (prints the three-act narrative + target list), and declare the target names from [ARCHITECTURE §16.4](../../docs/ARCHITECTURE_AND_IMPLEMENTATION_PLAN.md#164-makefile-contract-implementation-target): `doctor`, `install-pipefy-tools`, `install-cursor-demo`, `install-nat-demo`, `demo-cursor`, `demo-nat`, `tour`. Targets not yet implemented should print a clear "not implemented yet (task N.N)" message and exit non-zero. Support `SCENARIO ?= inventory`.
    - **Why**: Establishes the operator contract early; later tasks fill each target in.
    - **Pattern**: `.PHONY` targets; `make help` as default goal; keep target names exactly as the docs (`demo-nat`, not `nat-demo`, per D11).
    - **Verify**: `make help` lists every target; `make` with no args shows help.
    - **Integration**: Tasks 2.0–5.0 replace the stubs for `doctor`, `install-*`, `demo-*`, `tour`.
  - [x] 1.3 Create lint-only CI workflow
    - **File**: `.github/workflows/ci.yml` (create new)
    - **What**: GitHub Actions workflow on push/PR that sets up Python 3.11, installs `uv`, and runs `uv run ruff check .` and `uv run ruff format --check .`. No Pipefy/NIM/Cursor calls.
    - **Why**: FR-25 — cheap quality gate with no secrets/network.
    - **Pattern**: `astral-sh/setup-uv` action; single `lint` job.
    - **Verify**: `act` or a pushed branch shows the job passing; locally `uv run ruff check .` is green.
  - [x] 1.4 Verify `LICENSE` and `.gitignore` are correct
    - **File**: `LICENSE`, `.gitignore` (verify existing)
    - **What**: Confirm MIT `LICENSE` exists and README links it; confirm `.gitignore` already ignores `.env`, `eval/fixtures/live/`, `eval/transcripts/`, `private/CONTEXT.md`.
    - **Why**: FR-24/27 — public-repo safety; avoid committing secrets/fixtures.
    - **Pattern**: Files already created in planning; this is a check, not a rewrite.
    - **Verify**: `test -f LICENSE` and `git check-ignore .env eval/fixtures/live/x.json` both succeed.

- [x] 2.0 **Pipefy tool chain & `make doctor` preflight** _(Sprint 0)_

  **Trigger:** Operator runs `make install-pipefy-tools` then `make doctor` after editing `.env`.
  **Enables:** Both harnesses (binary on PATH + frozen `tool_allowlist.yml` for NAT `include:`).
  **Depends on:** 1.0 (Makefile skeleton).
  **Acceptance criteria:** `make install-pipefy-tools` puts `pipefy` and `pipefy-mcp-server` on PATH at the pinned tag; `make doctor` prints one `✓`/`✗` per check from [ARCHITECTURE §16.4](../../docs/ARCHITECTURE_AND_IMPLEMENTATION_PLAN.md#164-makefile-contract-implementation-target), exits non-zero when a required check fails, and never prints secret values; `configs/tool_allowlist.yml` contains 8–15 real tool names from the pinned version.

  - [x] 2.1 Implement `make install-pipefy-tools`
    - **File**: `Makefile` (modify existing)
    - **What**: Target that installs from [`pipefy/ai-toolkit`](https://github.com/pipefy/ai-toolkit) at a pinned tag — either the official `install.sh` (`--client cursor`) or `uv tool install` with workspace-member flags (`pipefy-sdk`, `pipefy-auth` via `#subdirectory=packages/...`). Define `PIPEFY_TOOLKIT_REF ?= v0.2.0-beta.2` at the top of the Makefile.
    - **Why**: FR-1 — reproducible install of the MCP server + CLI.
    - **Pattern**: Follow the install commands in the `pipefy/ai-toolkit` README; avoid `@latest`.
    - **Verify**: After running, `pipefy --version` and `command -v pipefy-mcp-server` both succeed.
  - [x] 2.2 Implement `scripts/doctor.sh` preflight
    - **File**: `scripts/doctor.sh` (create new)
    - **What**: Check `uv`, `pipefy`, `pipefy-mcp-server` on PATH; check required env vars present (print `set`/`missing`, never the value); per-harness optional keys (`CURSOR_API_KEY`, `NVIDIA_API_KEY`) warn (not fail) if running only one harness; run read-only `pipefy pipe list --json` and assert a non-empty array. Print `✓`/`✗` per line; `exit 1` if any required check fails.
    - **Why**: FR-2/4 — trustworthy preflight before spending LLM calls.
    - **Pattern**: POSIX `sh`; helper `check() { ... }`; never `echo "$CURSOR_API_KEY"`.
    - **Verify**: With a complete `.env`, exits 0 and all required lines are `✓`; unset `DEMO_PIPE_ID` → exits non-zero with a clear `✗` line; grep the output to confirm no secret value is printed.
    - **Integration**: Called by `make doctor` (2.3) and reused by `make tour` (5.5).
  - [x] 2.3 Wire `make doctor`
    - **File**: `Makefile` (modify existing)
    - **What**: `doctor` target that loads `.env` and runs `scripts/doctor.sh`, propagating its exit code.
    - **Why**: FR-2 — one-command preflight.
    - **Pattern**: `set -a; . ./.env; set +a` before invoking the script.
    - **Verify**: `make doctor` mirrors `scripts/doctor.sh` exit code and output.
  - [x] 2.4 Freeze `configs/tool_allowlist.yml`
    - **File**: `configs/tool_allowlist.yml` (create new)
    - **What**: List 8–15 MCP tool names for `inventory` + read (e.g. pipe list/get, card list/get, organization metadata), copied verbatim from the pinned version's `PIPEFY_TOOL_NAMES` (`packages/mcp/src/pipefy_mcp/tools/registry.py`) — discovered via `nat mcp client tool list --transport stdio --command pipefy-mcp-server` or MCP Inspector. Include a comment with the toolkit tag used.
    - **Why**: FR-3 / D4 — curb tool sprawl; this file is the source of the NAT `include:`.
    - **Pattern**: Names MUST match upstream exactly (validate at runtime, do not guess).
    - **Verify**: Every name in the file appears in `nat mcp client tool list` output for the pinned version.
    - **Integration**: Consumed by `configs/pipefy_nat_workflow.yml` `include:` (4.1).

- [x] 3.0 **Cursor SDK harness — `inventory` end-to-end** _(Sprint 1)_

  **Trigger:** `make demo-cursor SCENARIO=inventory`.
  **Enables:** Act 2 of `make tour`; an answer artifact for the eval comparison.
  **Depends on:** 2.0 (binary on PATH; `.env` validated by doctor).
  **Acceptance criteria:** `make demo-cursor SCENARIO=inventory` prints a coherent answer naming pipes that also appear in the CLI baseline, logs `agent_id` and `run.id`, shows at least one tool call, and uses exit codes 0/1/2 as specified.

  - [x] 3.1 Create the `inventory` prompt
    - **File**: `demos/prompts/inventory.txt` (create new)
    - **What**: Fixed prompt: "List all pipes I have access to in the organization and the number of open cards in each." (org-wide; uses `DEMO_ORG_ID`).
    - **Why**: FR-14 — diffable, shared prompt for both harnesses.
    - **Pattern**: Plain text, no shell escaping; one scenario per file.
    - **Verify**: File exists and is non-empty.
    - **Integration**: Read by both `demos/01_cursor_pipefy_ops.py` (3.2) and `demos/02_nat_smoke.sh` (4.2).
  - [x] 3.2 Implement `demos/01_cursor_pipefy_ops.py`
    - **File**: `demos/01_cursor_pipefy_ops.py` (create new)
    - **What**: Load `.env` (`python-dotenv`); read `--scenario` (default `inventory`) and load `demos/prompts/<scenario>.txt`; `with Agent.create(model="composer-2.5", local=LocalAgentOptions(cwd=os.getcwd()), mcp_servers={"pipefy": StdioMcpServerConfig(command="pipefy-mcp-server", env={...service account...})}) as agent:`; `run = agent.send(prompt)`; stream tool-call lines and print final `run.text()`; log `agent.agent_id` and `run.id`. Exit 1 on `CursorAgentError`, exit 2 on `result.status == "error"`, else 0.
    - **Why**: FR-5/6/7/8 — programmatic Cursor harness over Pipefy MCP.
    - **Pattern**: Cursor Python SDK docs (`Agent.create`, `StdioMcpServerConfig`, streaming `run.messages()` with `message.type == "tool_call"`, `CursorAgentError`). Inline MCP only (no `setting_sources`).
    - **Verify**: `make demo-cursor SCENARIO=inventory` prints `agent_id`/`run_id`, a `[tool] ...` line, and a pipe-naming answer; `echo $?` is 0.
  - [x] 3.3 Implement `make install-cursor-demo`
    - **File**: `Makefile` (modify existing)
    - **What**: `uv pip install cursor-sdk python-dotenv` (pin minimum versions once tested).
    - **Why**: FR — explicit install order for the Cursor path.
    - **Pattern**: Mirror `install-pipefy-tools` style.
    - **Verify**: `uv run python -c "import cursor_sdk, dotenv"` exits 0.
  - [x] 3.4 Implement `make demo-cursor`
    - **File**: `Makefile` (modify existing)
    - **What**: Run `uv run python demos/01_cursor_pipefy_ops.py --scenario $(SCENARIO)` with `.env` loaded.
    - **Why**: FR-9 — one command per scenario.
    - **Verify**: `make demo-cursor` (default) runs the `inventory` scenario.

- [x] 4.0 **NVIDIA NAT harness — `inventory` end-to-end** _(Sprint 1)_

  **Trigger:** `make demo-nat SCENARIO=inventory`.
  **Enables:** Act 3 of `make tour`; second answer artifact for eval.
  **Depends on:** 2.0 (frozen `tool_allowlist.yml` for `include:`). Independent of 3.0.
  **Acceptance criteria:** `make demo-nat SCENARIO=inventory` completes via NIM, shows NAT tool discovery + at least one tool call (`verbose: true`), and answers consistently with the CLI baseline; requires only `NVIDIA_API_KEY` + Pipefy credentials.

  - [x] 4.1 Author `configs/pipefy_nat_workflow.yml`
    - **File**: `configs/pipefy_nat_workflow.yml` (create new)
    - **What**: `llms.nim_llm: {_type: nim, model_name: meta/llama-3.1-8b-instruct}`; `function_groups.pipefy: {_type: mcp_client, server: {transport: stdio, command: pipefy-mcp-server, env: {...}}, include: [search_pipes, get_cards]}` (2-tool inventory subset); `workflow: {_type: react_agent, tool_names: [pipefy], llm_name: nim_llm, max_iterations: 22, verbose: true}` (D10; supersedes original MVP default `8`).
    - **Why**: FR-10 / D9 / D10 — declarative NAT workflow over the same MCP server.
    - **Pattern**: NAT MCP-client docs + Hello World in [NVIDIA/NeMo-Agent-Toolkit](https://github.com/NVIDIA/NeMo-Agent-Toolkit). Keep `model_name` a single, easily swapped value (8b ↔ 70b).
    - **Verify**: `nat run --config_file configs/pipefy_nat_workflow.yml --input "$(cat demos/prompts/inventory.txt)"` discovers tools and answers; tool names resolve against the pinned server.
    - **Integration**: `include:` mirrors `configs/tool_allowlist.yml` (2.4).
  - [x] 4.2 Implement `demos/02_nat_smoke.sh`
    - **File**: `demos/02_nat_smoke.sh` (create new)
    - **What**: Take a scenario arg (default `inventory`), load `.env`, read `demos/prompts/<scenario>.txt`, and run `nat run --config_file "${NAT_CONFIG_FILE:-configs/pipefy_nat_workflow.yml}" --input "<prompt>"` with labeled section output.
    - **Why**: FR-11 — scriptable NAT invocation parallel to the Cursor script.
    - **Pattern**: POSIX `sh`; labeled `=== Act 3: ... ===` header.
    - **Verify**: `./demos/02_nat_smoke.sh inventory` runs end-to-end.
  - [x] 4.3 Implement `make install-nat-demo`
    - **File**: `Makefile` (modify existing)
    - **What**: `uv pip install "nvidia-nat[mcp]"` (pin minimum version once tested).
    - **Why**: FR — explicit install for the NAT path.
    - **Verify**: `uv run nat --help` works.
  - [x] 4.4 Implement `make demo-nat`
    - **File**: `Makefile` (modify existing)
    - **What**: Run `demos/02_nat_smoke.sh $(SCENARIO)` with `.env` loaded.
    - **Why**: FR-12 — same scenario interface as `demo-cursor`.
    - **Verify**: `make demo-nat` runs the `inventory` scenario.

- [x] 5.0 **Tour, evaluation & operator experience** _(Sprint 2)_

  **Trigger:** `make tour` after both harnesses work.
  **Enables:** The "aha" side-by-side comparison + automated fact check; the close-out.
  **Depends on:** 3.0 and 4.0.
  **Acceptance criteria:** `make tour` prints the three labeled layers, runs the CLI baseline + both demos on `inventory`, and prints `✓` from `eval/compare.py`; `uv run pytest tests/ -v` passes; the other two prompt files exist and run via `SCENARIO=`; TRY_IT_YOURSELF Steps 0–4 work as written.

  - [x] 5.1 Create remaining prompt files
    - **File**: `demos/prompts/stale_cards.txt`, `demos/prompts/summary.txt` (create new)
    - **What**: `stale_cards` (cards in `DEMO_PHASE_NAME` > 7 days in pipe `DEMO_PIPE_ID`); `summary` (5 most recently created open cards with title/phase/assignees).
    - **Why**: FR-14/15 — best-effort scenarios runnable via `SCENARIO=` (not gated).
    - **Pattern**: Mirror `inventory.txt`; reference env vars by name in the prompt text.
    - **Verify**: `make demo-cursor SCENARIO=stale_cards` and `SCENARIO=summary` load the right prompt (smoke).
  - [x] 5.2 Implement `eval/ground_truth.sh`
    - **File**: `eval/ground_truth.sh` (create new)
    - **What**: Take a scenario arg; run the matching `pipefy ... --json` command(s) and write the baseline to `eval/fixtures/live/<scenario>.json` (gitignored).
    - **Why**: FR-20 — deterministic ground truth from the CLI.
    - **Pattern**: For `inventory`: `pipefy pipe list --json`.
    - **Verify**: `./eval/ground_truth.sh inventory` writes a non-empty JSON file under `eval/fixtures/live/`.
  - [x] 5.3 Implement `eval/compare.py` + unit tests
    - **File**: `eval/compare.py` (create new), `tests/test_compare.py` (create new)
    - **What**: Pure functions that extract `pipe_count` and `pipe_names` from a CLI JSON baseline and from an agent answer (text), then return pass/fail using **count match + pipe-name substring** (D12). CLI entry: `compare.py --baseline <json> --answer <txt>` prints `✓`/`✗` and exits 0/1. Tests cover: exact match passes, missing pipe fails, count mismatch fails, case-insensitive substring.
    - **Why**: FR-21 — non-flaky fact check; the only offline-testable logic.
    - **Pattern**: Keep extraction pure (input str/dict → values) so tests need no network.
    - **Verify**: `uv run pytest tests/test_compare.py -v` passes.
    - **Integration**: Invoked by `make tour` (5.5) against `inventory`.
  - [x] 5.4 Commit a synthetic example fixture
    - **File**: `eval/fixtures/example/inventory.json` (create new)
    - **What**: Small synthetic `pipe list --json`-shaped fixture (no real org data) used by tests and as a documented sample.
    - **Why**: FR-23 / D13 — public-repo-safe example; `live/` stays gitignored.
    - **Pattern**: Match the CLI JSON shape; fictional pipe names/IDs.
    - **Verify**: `tests/test_compare.py` loads it and passes; `git check-ignore eval/fixtures/live/x.json` confirms only `live/` is ignored.
  - [x] 5.5 Implement `make tour`
    - **File**: `Makefile` (modify existing)
    - **What**: Print the three labeled layers; run `eval/ground_truth.sh inventory`; run `demo-cursor` and `demo-nat` on `inventory`; run `eval/compare.py` and print `✓`/`✗`. Avoid raw JSON dumps unless `VERBOSE=1`.
    - **Why**: FR-17/18/22 — the end-to-end operator experience + fact check.
    - **Pattern**: Labeled sections per [ARCHITECTURE §16.5](../../docs/ARCHITECTURE_AND_IMPLEMENTATION_PLAN.md).
    - **Verify**: `make tour` prints all three acts and a final `✓` on a healthy run.
  - [x] 5.6 Finalize `docs/TRY_IT_YOURSELF.md`
    - **File**: `docs/TRY_IT_YOURSELF.md` (modify existing)
    - **What**: Reconcile every command in Steps 0–4 with the real targets/flags built above; fix any drift (target names, install commands, scenario flags).
    - **Why**: FR-19 — clone-and-run reproducibility.
    - **Verify**: Each command block in Steps 0–4 has a corresponding working target; a dry read-through finds no command that does not exist.

- [x] 6.0 **Close-out: initial commit & planning-artifact reconciliation**

  **Trigger:** MVP is green (task 5.0 acceptance met).
  **Enables:** Trustworthy baseline for the stretch PRDs (2/3/4).
  **Depends on:** 5.0.
  **Acceptance criteria:** The three planning artifacts reflect what was built, and an initial commit exists (no remote push).

  - [x] 6.1 Reconcile ARCHITECTURE §14
    - **File**: `docs/ARCHITECTURE_AND_IMPLEMENTATION_PLAN.md` (modify existing)
    - **What**: Tick Phase 0–4 boxes/exit criteria that are met; record the frozen `pipefy/ai-toolkit` tag and the observed tool count.
    - **Why**: FR-28 — backbone stays accurate.
    - **Verify**: §14 reflects the shipped state; no "planned" markers for delivered targets.
  - [x] 6.2 Update the PRD roadmap index
    - **File**: `product/prd/README.md` (modify existing)
    - **What**: Move PRD-1 status from "Draft for sign-off" to "Done"; note any scope deltas.
    - **Why**: FR-28 — living roadmap.
    - **Verify**: PRD-1 row shows the new status.
  - [x] 6.3 Reconcile OPEN_DECISIONS
    - **File**: `docs/OPEN_DECISIONS.md` (modify existing)
    - **What**: Move any decision settled during the build (e.g. the `70b` key-tier outcome, the exact pinned tag) to **Resolved** with date.
    - **Why**: FR-28 — cross-cutting decision log stays current.
    - **Verify**: No build-time decision remains in an "open" section.
  