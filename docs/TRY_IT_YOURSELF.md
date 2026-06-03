# Try It Yourself — Hands-On Tour (Pipefy + Cursor + NVIDIA)

**Audience:** Developers and operators cloning this repo who want to **run** the orchestration on their own machine—not watch a recording.

**Time:** ~20–30 minutes for the full tour (less if you skip optional steps).

**What you will experience:** The same **Pipefy** data accessed three ways—deterministic CLI, **Cursor SDK** agent, **NVIDIA NeMo Agent Toolkit (NAT)** agent—so the “bridge” between ecosystems is visible in your terminal.

---

## The story in one paragraph

**Pipefy** holds your process data (pipes, phases, cards). The **official Pipefy AI Toolkit** ([pipefy/ai-toolkit](https://github.com/pipefy/ai-toolkit)) ships `pipefy-mcp-server`, which exposes that data as **MCP tools**. **Cursor** and **NVIDIA** are two different **agent harnesses** that call those same tools and reason over the results. This repo does not reimplement Pipefy APIs—it shows how to **orchestrate** them with a single MCP contract and two production-style runtimes.

```
  You (terminal)
       │
       ├─► Step 1: pipefy CLI     ──► Pipefy API     (ground truth, no AI)
       ├─► Step 2: Cursor SDK     ──► MCP ──► Pipefy  (Cursor agent harness)
       └─► Step 3: nat run        ──► MCP ──► Pipefy  (NVIDIA NAT + NIM)
```

> **Naming:** the numbered **Steps** below are the same as the three **Acts** in the [README](../README.md) and the architecture narrative ([Section 16.3](ARCHITECTURE_AND_IMPLEMENTATION_PLAN.md#163-the-three-act-narrative-guided-structure)): Step 1 = Act 1 (Pipefy CLI), Step 2 = Act 2 (Cursor), Step 3 = Act 3 (NVIDIA), Step 4 = Encore (`make tour`).

---

## Before you start

### What you need

| Requirement | Why |
|-------------|-----|
| **macOS or Linux** (WSL2 OK) | Tested path for `uv` and stdio MCP |
| **Python 3.11+** | Matches pipefy-mcp-server |
| **[uv](https://docs.astral.sh/uv/)** | Install Pipefy tools and Python deps |
| **Pipefy account** + **service account** | Unattended API access (no browser during the tour) |
| **Cursor API key** | [Cursor Dashboard → API Keys](https://cursor.com/dashboard/api) |
| **NVIDIA API key** | [build.nvidia.com](https://build.nvidia.com/) for **NIM** |

You do **not** need an NVIDIA GPU for the core tour. GPU is only relevant for the optional embeddings phase described in the [architecture plan](ARCHITECTURE_AND_IMPLEMENTATION_PLAN.md).

### What you do *not* need

- Cursor IDE installed (the **Cursor SDK** runs from Python).
- A Pipefy production org with sensitive data (use a **sandbox** pipe).
- All 149 MCP tools configured (we curate a small allowlist in `configs/tool_allowlist.yml`—see [OPEN_DECISIONS.md](OPEN_DECISIONS.md) D4).

### Install order (reference)

Run these once before Steps 2–4 (Step 1 installs Pipefy tools; Steps 2–3 install harness deps):

```bash
make install-pipefy-tools   # pipefy CLI + pipefy-mcp-server @ v0.2.0-beta.2 (override: PIPEFY_TOOLKIT_REF=)
make install-cursor-demo      # cursor-sdk + python-dotenv
make install-nat-demo         # nvidia-nat[mcp,langchain]
```

List all targets: `make help` (default goal).

---

## Step 0 — Clone and configure (5 min)

```bash
git clone https://github.com/<your-org>/pipefy-agent-bridge.git
cd pipefy-agent-bridge
cp .env.example .env
```

Replace `<your-org>` with your GitHub org or username (see [OPEN_DECISIONS.md](OPEN_DECISIONS.md) D3).

Edit `.env` (see [.env.example](../.env.example)):

| Variable | Where to get it |
|----------|-----------------|
| `PIPEFY_SERVICE_ACCOUNT_CLIENT_ID` | Pipefy Admin → Service Accounts |
| `PIPEFY_SERVICE_ACCOUNT_CLIENT_SECRET` | Same |
| `DEMO_ORG_ID` | Organization ID for the org-wide **inventory** scenario |
| `DEMO_PIPE_ID` | Numeric ID of a pipe you are allowed to read (`stale_cards`, `summary`) |
| `DEMO_PHASE_NAME` | Phase name as shown in Pipefy UI (for `stale_cards`) |
| `CURSOR_API_KEY` | Cursor Dashboard |
| `NVIDIA_API_KEY` | NVIDIA Build |

**Pipefy tip:** Grant the service account access to the demo pipe (and org, for inventory)—keeps the blast radius small.

**Sanity check:**

```bash
make doctor
```

Expected: one `✓`/`✗` line per check covering `uv`, `pipefy`, `pipefy-mcp-server`, required env vars (`PIPEFY_*`, `DEMO_PIPE_ID`, `DEMO_ORG_ID`), optional warnings for `CURSOR_API_KEY` / `NVIDIA_API_KEY`, and a read-only `pipefy pipe list --json` ping. Exits non-zero if any required check fails; never prints secret values (only `set`/`missing`). Full check list: [ARCHITECTURE plan — Section 16.4](ARCHITECTURE_AND_IMPLEMENTATION_PLAN.md#164-makefile-contract-implementation-target).

**Optional — dev tooling for unit tests:**

```bash
uv sync --extra dev
uv run pytest tests/ -v
```

---

## Step 1 — Meet Pipefy without AI (5 min)

**Goal:** See real Pipefy data and establish **ground truth** before any agent runs.

```bash
make install-pipefy-tools

# List pipes (deterministic JSON)
pipefy pipe list --json

# Inspect your demo pipe
pipefy card list --pipe-id "$DEMO_PIPE_ID" --json | head
```

**What you should see:** JSON listing pipes/cards from **Pipefy’s GraphQL API** via the official toolkit—no LLM involved.

**Why this step matters:** When Step 2 or 3 returns pipe names or card counts, you can compare them to this output and verify the agent used real tools rather than inventing data.

**Baseline snapshot (used by `make tour`):**

```bash
./eval/ground_truth.sh inventory
# writes eval/fixtures/live/inventory.json (gitignored)
```

---

## Step 2 — Same data through the Cursor harness (7 min)

**Goal:** Run a **Cursor SDK** agent that calls **Pipefy MCP** tools (`pipefy-mcp-server` subprocess).

```bash
make install-cursor-demo
make demo-cursor
```

Default scenario is **`inventory`** (org-wide pipe list). Override with `SCENARIO=`:

```bash
make demo-cursor SCENARIO=stale_cards
make demo-cursor SCENARIO=summary
```

Prompts live in `demos/prompts/<scenario>.txt`.

**What happens under the hood:**

1. `demos/01_cursor_pipefy_ops.py` loads `.env` and reads the prompt file.
2. `Agent.create(...)` with `local=LocalAgentOptions` and `StdioMcpServerConfig(command="pipefy-mcp-server")`.
3. The Cursor agent issues **tool_call** events → MCP → **Pipefy** GraphQL.
4. The script prints the final answer and logs `agent_id` / `run.id`.

**What you should see:**

- Lines like `[tool] …` from the SDK stream.
- A natural-language summary consistent with Step 1 (for `inventory`: pipe names and counts).

**Cursor concepts to notice:**

- Explicit **local** runtime (agent runs on your machine).
- **MCP** as the only tool interface to Pipefy.
- Exit codes: `0` success, `1` `CursorAgentError`, `2` run `status == "error"`.

Docs: [Cursor Python SDK](https://cursor.com/docs/sdk/python)

---

## Step 3 — Same pattern through the NVIDIA harness (7 min)

**Goal:** Run **NeMo Agent Toolkit** with a **NIM** LLM and the **same** `pipefy-mcp-server` via `mcp_client` (stdio).

```bash
make install-nat-demo
make demo-nat
```

Equivalent manual invocation (same prompt as the Makefile target):

```bash
set -a && . ./.env && set +a
nat run --config_file "${NAT_CONFIG_FILE:-configs/pipefy_nat_workflow.yml}" \
  --input "$(cat demos/prompts/inventory.txt)"
```

**What happens under the hood:**

1. NAT loads `configs/pipefy_nat_workflow.yml`. The repo curates **12** tools in `configs/tool_allowlist.yml`, but the shipped NAT workflow exposes only **`search_pipes`** and **`get_cards`** so `meta/llama-3.1-8b-instruct` stays on the inventory path (see [LEARNINGS.md](LEARNINGS.md)).
2. `function_groups.pipefy` connects to MCP with `transport: stdio` and `command: pipefy-mcp-server`.
3. `react_agent` uses **NIM** (`_type: nim`) to plan and call tools (`max_iterations: 22` → `recursion_limit` 46; maps to NAT `max_tool_calls`; see D10 / [LEARNINGS.md](LEARNINGS.md)).
4. Verbose logging shows tool iterations (`demos/02_nat_smoke.sh` prints an Act 3 header). Agent steps often land on **stderr**; the tour captures **`2>&1`** before answer extraction.

**8b expectations:** The default NIM model can hit recursion limits, invent `search_pipes` filters, or stop with an incomplete `Final Answer`. `demos/02_nat_smoke.sh` fails on workflow errors, missing `Final Answer:`, or “no pipes” when tools returned data. A single `make demo-nat` may need **2–3 runs** on busy orgs; `make tour` retries NAT automatically (Step 4).

> **Reliability contract:** **Step 2 (Cursor)** is the guaranteed-green path; **Step 3 (NAT, 8b)** is **best-effort** (compare-gated, retried in the tour). For a more reliable first attempt, set `NIM_MODEL=meta/llama-3.1-70b-instruct` if your NVIDIA tier allows it (opt-in; see [OPEN_DECISIONS.md](OPEN_DECISIONS.md) D18/D19). First-attempt NAT reliability is a measured objective in PRD-2.

**What you should see:**

- NAT startup banner and tool discovery.
- Tool calls against Pipefy (same backend as Step 2).
- An answer **semantically aligned** with Steps 1–2 (wording may differ: **NIM ≠ Composer**).

**Optional — same scenarios as Cursor:**

```bash
make demo-nat SCENARIO=stale_cards
make demo-nat SCENARIO=summary
```

**NVIDIA concepts to notice:**

- **Framework-agnostic** orchestration (YAML, not Cursor-specific).
- **MCP client** as documented by NVIDIA for third-party tools.
- Path to profiler/eval (stretch) without changing the Pipefy integration.

Docs: [NeMo Agent Toolkit](https://docs.nvidia.com/nemo/agent-toolkit/latest/index.html) · [MCP client](https://docs.nvidia.com/nemo/agent-toolkit/latest/build-workflows/mcp-client.html)

---

## Step 4 — The “aha” comparison (3 min)

Run the full guided tour (requires `CURSOR_API_KEY`, `NVIDIA_API_KEY`, and Pipefy credentials in `.env`):

```bash
make tour
```

This runs `scripts/tour.sh`, which:

1. Prints a short intro and the three **Acts** (CLI / Cursor / NAT). Expect **several minutes** when both API keys are set (remote LLM calls per act).
2. **Act 1:** `./eval/ground_truth.sh inventory` → `eval/fixtures/live/inventory.json`, then a one-line summary of **listed** pipe names (not a raw JSON dump unless `VERBOSE=1`). Large orgs may show `pipes_truncated: true` while `pipesCount` is org-wide—Encore compares against the **visible page** (see [LEARNINGS.md](LEARNINGS.md)).
3. **Act 2:** `demo-cursor` on `inventory` (stdout captured). On non-zero exit, the tour **retries once**.
4. **Act 3:** `demo-nat` on `inventory` with stdout+stderr captured (`2>&1`), then `scripts/extract_nat_answer.py` (last `Workflow Result:` / `Final Answer`). Up to **3** attempts; each attempt must pass `eval/compare.py` on the extracted answer before the tour continues. If all attempts fail, Act 3 is marked `✗` (Encore may still run for diagnosis).
5. **Encore:** `eval/compare.py` again on Cursor and NAT answers vs the CLI baseline—printing `✓`/`✗` per line (count + pipe-name substring match; truncation-aware; see D12 in [OPEN_DECISIONS.md](OPEN_DECISIONS.md)).

Tour exits `0` only when every step and both Encore lines pass. Details: [ARCHITECTURE §16.5](ARCHITECTURE_AND_IMPLEMENTATION_PLAN.md#165-console-output-guidelines-implementation).

**Tour options:**

| Variable | Effect |
|----------|--------|
| `VERBOSE=1` | Dump baseline JSON and captured agent answers |
| `TOUR_KEEP_TMP=1` | Keep temp answer files (path printed on exit) |

**Manual fact check (offline, no LLM):**

```bash
uv run python eval/compare.py \
  --baseline eval/fixtures/live/inventory.json \
  --answer /path/to/agent_answer.txt
```

**Architecture takeaway:**

| Layer | Technology | Role in this repo |
|-------|------------|-------------------|
| Data & tools | **Pipefy** + pipefy-mcp-server | Source of truth via MCP |
| Harness A | **Cursor SDK** | Developer/agent lifecycle, IDE-adjacent automation |
| Harness B | **NVIDIA NAT** + **NIM** | Declarative workflows, profiling, and evaluation path |

---

## Three hands-on scenarios (pick any after the tour)

Each scenario is a **prompt file** + **`SCENARIO=`** on both harnesses—no improvisation required.

| ID | Command | Question you are asking Pipefy |
|----|---------|------------------------------|
| **A** | `make demo-cursor SCENARIO=inventory` | What pipes exist and how many open cards? (org `DEMO_ORG_ID`) |
| **B** | `make demo-cursor SCENARIO=stale_cards` | Which cards are stuck in `DEMO_PHASE_NAME` > 7 days in `DEMO_PIPE_ID`? |
| **C** | `make demo-cursor SCENARIO=summary` | Summarize the 5 newest open cards in `DEMO_PIPE_ID` (title, phase, assignees) |

Run the same scenario on NVIDIA:

```bash
make demo-nat SCENARIO=inventory
```

Only **`inventory`** is wired into `make tour` and `eval/compare.py`. Scenarios B and C are best-effort (no automated fact check in MVP).

Details: [ARCHITECTURE plan — Section 15](ARCHITECTURE_AND_IMPLEMENTATION_PLAN.md#15-hands-on-scenarios-reproducible-locally).

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `pipefy-mcp-server: command not found` | Tools not installed | `make install-pipefy-tools` |
| Empty pipe list | Service account not in org / pipe | Pipefy Admin → add account to org and demo pipe |
| `error: .env missing` | No `.env` file | `cp .env.example .env` |
| `AuthenticationError` (Cursor) | Invalid `CURSOR_API_KEY` | Regenerate key; no extra spaces in `.env` |
| NAT cannot reach NIM | Missing `NVIDIA_API_KEY` | Set in `.env`; `make doctor` warns if missing |
| Agent answer unrelated to data | No tool calls | Check MCP env vars; run `make doctor` |
| NAT tool not found | Wrong name in `include:` | Regenerate `configs/tool_allowlist.yml` from pinned toolkit |
| Tour fact check `✗` | Model omitted a pipe name, or baseline uses truncated `pipes[]` while the answer cites only `pipesCount` | `VERBOSE=1` or `TOUR_KEEP_TMP=1`; see [LEARNINGS.md](LEARNINGS.md); re-run `make tour` |
| `Recursion limit` / incomplete NAT answer | 8b exhausted tool loop or stopped early | Re-run `make demo-nat` or `make tour` (NAT retries up to 3×); optional `70b` in workflow YAML |
| `demo-nat` passed but tour Act 3 `✗` | Extracted answer failed compare before Encore | Inspect temp answer with `TOUR_KEEP_TMP=1`; ensure every listed pipe name appears in the Final Answer |
| Encore `✗` on count with “5 … 274 total” | Answer cites org total and page size | Expected when compare is truncation-aware; if still failing, check pipe **names** in the answer |

If you are blocked, open an issue with redacted `make doctor` output (never paste secrets).

---

## Suggested path for a 15-minute walkthrough

1. Read [README](../README.md) (2 min).
2. Skim architecture diagram in [ARCHITECTURE_AND_IMPLEMENTATION_PLAN.md](ARCHITECTURE_AND_IMPLEMENTATION_PLAN.md#5-architectural-overview) (3 min).
3. Run **Step 0 → Step 3** (install targets + `make doctor` once) (10 min).
4. Optional: `make tour` or one extra `SCENARIO=` (5 min).

No video required—your terminal is the proof.

---

## Optional: recording for async distribution

If someone cannot run locally, a short asciinema can supplement the docs. **Reproducibility on a fresh clone** remains the primary success metric. Recording is a low-priority secondary artifact; if added, keep the notes in this section rather than a separate file (see [OPEN_DECISIONS.md](OPEN_DECISIONS.md) D14).

---

## Makefile targets (shipped)

| Target | Purpose |
|--------|---------|
| `make help` | Three-act narrative + target list (default) |
| `make doctor` | Preflight (`scripts/doctor.sh`) |
| `make install-pipefy-tools` | `pipefy` + `pipefy-mcp-server` @ `PIPEFY_TOOLKIT_REF` |
| `make install-cursor-demo` | `cursor-sdk` + `python-dotenv` |
| `make install-nat-demo` | `nvidia-nat[mcp,langchain]` |
| `make demo-cursor` | `demos/01_cursor_pipefy_ops.py` (`SCENARIO` defaults to `inventory`) |
| `make demo-nat` | `demos/02_nat_smoke.sh` (`SCENARIO` defaults to `inventory`) |
| `make tour` | Acts 1–3 + `eval/compare.py` on `inventory` |

---

*One MCP bridge; **Pipefy** data; **Cursor** and **NVIDIA** harnesses.*
