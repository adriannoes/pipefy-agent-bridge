# Benchmarks — reliability & latency

Public, reproducible numbers for golden eval scenarios across the **Cursor SDK** and **NVIDIA NAT** harnesses. Live runs are **operator-invoked** (needs `.env` with Pipefy + NVIDIA keys); CI stays lint-only.

> **Status:** **Cursor live run (2026-06-04)** — all three golden scenarios scored against `eval/fixtures/live/*.json` after `eval/ground_truth.sh` (demo pipe **Analytics**, id `306996636`; stale phase **Review**). **NAT** rows unchanged from **2026-06-03** inventory-only run (no new NAT batches in this refresh). Pre-fix inventory table (example fixture) is archived in git history — do not use for D18/D19.

## Scenario coverage matrix

| Scenario | Demo (`SCENARIO=`) | Ground truth (`eval/ground_truth.sh`) | Golden eval (`make eval`) | Live numbers in this doc |
| --- | --- | --- | --- | --- |
| `inventory` | Yes | Yes (`pipefy pipe list --json`) | Yes | **Measured** (2026-06-04 Cursor; 2026-06-03 NAT 8b) |
| `stale_cards` | Yes | Yes (`capture_scenario_baseline.py` + read-only GraphQL) | Yes | **Measured** (2026-06-04 Cursor only) |
| `summary` | Yes | Yes (same capture path) | Yes | **Measured** (2026-06-04 Cursor only) |

Scoring uses `eval/fixtures/live/<scenario>.json` (gitignored). Committed `eval/fixtures/example/*.json` files document schema and validate `eval/golden.yaml` `expect` facts only.

## Run metadata

| Field | Value |
| --- | --- |
| **Run date (UTC)** | `2026-06-04` _(Cursor: all scenarios; NAT: unchanged from `2026-06-03`)_ |
| **Demo pipe (card scenarios)** | **Analytics** (`306996636`) — discovered via Pipefy MCP `search_pipes` |
| **Demo phase (`stale_cards`)** | `Review` _(phase name as in Pipefy UI)_ |
| **`pipefy/ai-toolkit` tag** | `v0.2.0-beta.2` _(Makefile `PIPEFY_TOOLKIT_REF`; confirm with `pipefy --version`)_ |
| **`cursor-sdk`** | `0.1.6` _(Makefile `CURSOR_SDK_VERSION`)_ |
| **`nvidia-nat` (+ profiler extra)** | `1.7.0` _(Makefile `NVIDIA_NAT_VERSION`; profiler via `nvidia-nat-profiler`)_ |
| **NIM model (NAT)** | `meta/llama-3.1-8b-instruct` _(default; override with `EVAL_ARGS=--model …` or `NIM_MODEL=…`)_ |
| **Golden scenarios** | `inventory`, `stale_cards`, `summary` (`eval/golden.yaml`; scoring uses `eval/fixtures/live/*.json`) |
| **Runner settings (NAT, inventory)** | `--runs 3`, `--retries 3`, `--harness nat` |
| **Runner settings (Cursor, all scenarios)** | `--runs 5`, `--retries 3`, `--harness cursor` |

Optional second row for **70b** (when NVIDIA tier allows): `meta/llama-3.1-70b-instruct` via `--model` / `NIM_MODEL` — **not measured** in the 2026-06-03 refresh (operator optional).

## Reliability & latency (per scenario × harness)

Measured with `eval/run_eval.py` scoring via `eval/compare.py` against the live baseline refreshed by `eval/ground_truth.sh`. Markdown tables include a **Scenario** column when pasted from `--emit-markdown`.

| Scenario | Harness | N | First-attempt % | With-retries % | Median latency (s) | P90 latency (s) |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| inventory | cursor | 5 | 100.0 | 100.0 | 54.84 | 63.44 |
| stale_cards | cursor | 5 | 100.0 | 100.0 | 28.86 | 31.64 |
| summary | cursor | 5 | 100.0 | 100.0 | 25.63 | 29.22 |
| inventory | nat | 3 | 33.3 | 66.7 | 35.92 | 205.60 |
| stale_cards | nat | — | _not measured_ | _not measured_ | _not measured_ | _not measured_ |
| summary | nat | — | _not measured_ | _not measured_ | _not measured_ | _not measured_ |

_Pre-fix (invalid baseline): inventory cursor 1 / 0% / 0% / 26.45 / 38.17; nat 3 / 0% / 0% / 19.86 / 31.27 — scored against `eval/fixtures/example/inventory.json`._

**Metric definitions**

- **First-attempt %:** share of episodes that passed on attempt 1 (`--retries` window still applies to episode structure, but only attempt 1 counts).
- **With-retries %:** share of episodes where any attempt in `1..retries` passed (runner stops early on first pass).
- **Median / P90 latency (s):** wall-clock **per episode** — sum of attempt latencies until pass or retries exhausted.

### Reproduce commands (inventory)

**Cursor (measured 2026-06-04):**

```bash
./eval/ground_truth.sh inventory
make eval EVAL_ARGS="--scenario inventory --harness cursor --runs 5 --retries 3 --json --emit-markdown"
```

**NAT, 8b (measured 2026-06-03):**

```bash
./eval/ground_truth.sh inventory
make eval EVAL_ARGS="--scenario inventory --harness nat --runs 3 --retries 3 --json --emit-markdown"
```

### Reproduce commands (stale_cards)

Requires `DEMO_PIPE_ID` and `DEMO_PHASE_NAME` in `.env` (phase name as shown in Pipefy UI). Demo pipe: Analytics (`306996636`), phase `Review`.

**Cursor (measured 2026-06-04):**

```bash
./eval/ground_truth.sh stale_cards
make eval EVAL_ARGS="--scenario stale_cards --harness cursor --runs 5 --retries 3 --json --emit-markdown"
```

**NAT (not measured in this refresh):**

```bash
./eval/ground_truth.sh stale_cards
make eval EVAL_ARGS="--scenario stale_cards --harness nat --runs 5 --retries 3 --json --emit-markdown"
```

Ground truth captures cards via read-only `pipefy graphql exec` (phase filter + `current_phase_age` > 7 days), writing `eval/fixtures/live/stale_cards.json`. When the live org has **zero** stale cards in that phase, scoring accepts a correct empty result.

### Reproduce commands (summary)

Requires `DEMO_PIPE_ID` in `.env` (demo pipe: Analytics `306996636`).

**Cursor (measured 2026-06-04):**

```bash
./eval/ground_truth.sh summary
make eval EVAL_ARGS="--scenario summary --harness cursor --runs 5 --retries 3 --json --emit-markdown"
```

**NAT (not measured in this refresh):**

```bash
./eval/ground_truth.sh summary
make eval EVAL_ARGS="--scenario summary --harness nat --runs 5 --retries 3 --json --emit-markdown"
```

Ground truth ranks **open** cards by `createdAt` (newest first, up to five) into `eval/fixtures/live/summary.json`.

### All scenarios in one runner invocation

After refreshing every live baseline:

```bash
./eval/ground_truth.sh inventory
./eval/ground_truth.sh stale_cards
./eval/ground_truth.sh summary
make eval EVAL_ARGS="--scenario all --harness both --runs 5 --retries 3 --json --emit-markdown"
```

## NAT profiler summary (shape reference)

Live profiling uses `make profile-nat` → `eval/profiles/<timestamp>.json` (gitignored). Works for any `SCENARIO=` (`inventory`, `stale_cards`, `summary`). The committed synthetic sample [`eval/fixtures/example/profile.json`](../eval/fixtures/example/profile.json) documents the **normalized** summary shape used in reports:

| Section | Fields (illustrative) |
| --- | --- |
| `run` | `scenario`, `harness`, `workflow_config`, `model`, `captured_at` |
| `summary` | `total_duration_s`, `agent_iteration_count`, `trace_step_count`, `tool_call_count`, `llm_invocation_count` |
| `workflow_runtime` | `mean_s`, `p50_s`, `p90_s`, `confidence_interval_90_s` |
| `iterations[]` | per-step `kind` (`llm` \| `tool`), `duration_ms`, optional `name` / `label` |
| `nat_profiler_artifacts` | pointers to NAT-native files under the profile output dir |

**Example (synthetic fixture, not a live measurement):** total wall time **18.42 s**, **4** agent iterations, **7** trace steps, **4** tool calls, **3** LLM calls; dominant steps include `search_pipes` (~890 ms) and repeated `get_cards` (~580–620 ms).

## Reproduce

Prerequisites: `cp .env.example .env`, fill Pipefy service account + `DEMO_ORG_ID`, `NVIDIA_API_KEY`, `CURSOR_API_KEY`; for card scenarios also `DEMO_PIPE_ID` and (for stale cards) `DEMO_PHASE_NAME`; `make doctor`; install harness deps as needed (`make install-cursor-demo`, `make install-nat-demo`).

### Reliability runner (golden eval)

Default (inventory only, both harnesses, 5 episodes, 8b NAT via env default):

```bash
make eval
```

Explicit flags (matches `eval/run_eval.py`):

```bash
make eval EVAL_ARGS="--scenario inventory --harness both --runs 5 --retries 3"
```

All golden scenarios:

```bash
make eval EVAL_ARGS="--scenario all --harness both --runs 5 --retries 3"
```

NAT-only, 70b override:

```bash
make eval EVAL_ARGS="--scenario inventory --harness nat --runs 5 --model meta/llama-3.1-70b-instruct"
```

Machine-readable summary:

```bash
make eval EVAL_ARGS="--json"
```

Paste-ready Markdown table for this doc:

```bash
make eval EVAL_ARGS="--emit-markdown"
```

### NAT profiler (timing / iterations)

```bash
make profile-nat
```

With scenario / model overrides (shell env, same as demo-nat):

```bash
make profile-nat SCENARIO=inventory
make profile-nat SCENARIO=stale_cards
make profile-nat SCENARIO=summary
NIM_MODEL=meta/llama-3.1-70b-instruct make profile-nat SCENARIO=inventory
```

Profiler output lands under `eval/profiles/` (ignored by git). Compare shape to [`eval/fixtures/example/profile.json`](../eval/fixtures/example/profile.json).

---

## Operator: run and paste (refresh)

When credentials or org data change, re-run and replace the **Run metadata** date and **Reliability & latency** table rows.

1. Refresh ground truth baselines (read-only Pipefy pull):

   ```bash
   ./eval/ground_truth.sh inventory
   ./eval/ground_truth.sh stale_cards   # needs DEMO_PIPE_ID + DEMO_PHASE_NAME
   ./eval/ground_truth.sh summary       # needs DEMO_PIPE_ID
   ```

   Ensures scoring uses current org data while golden `expect` facts stay fixture-based.

2. Run evaluation per scenario (8b default) or all at once:

   ```bash
   make eval EVAL_ARGS="--scenario inventory --harness both --runs 5 --retries 3 --json --emit-markdown"
   make eval EVAL_ARGS="--scenario stale_cards --harness both --runs 5 --retries 3 --json --emit-markdown"
   make eval EVAL_ARGS="--scenario summary --harness both --runs 5 --retries 3 --json --emit-markdown"
   # or:
   make eval EVAL_ARGS="--scenario all --harness both --runs 5 --retries 3 --json --emit-markdown"
   ```

   Copy the printed Markdown table into **Reliability & latency** above; set **Run date** to the UTC date of the run. Remove `_not measured_` placeholders for rows you refreshed.

3. _(Optional, tier permitting)_ Repeat inventory (or harder card scenarios) with 70b:

   ```bash
   make eval EVAL_ARGS="--scenario stale_cards --harness nat --runs 5 --model meta/llama-3.1-70b-instruct --emit-markdown"
   ```

4. Capture profiler bundles:

   ```bash
   make profile-nat SCENARIO=inventory
   make profile-nat SCENARIO=stale_cards
   make profile-nat SCENARIO=summary
   ```

   Summarize `summary` / `iterations` from the newest `eval/profiles/*.json` in **NAT profiler summary** (do not commit live profile JSON).

**Do not** paste organization IDs, tokens, pipe/card IDs from live baselines, or raw profile paths containing secrets into this document.
