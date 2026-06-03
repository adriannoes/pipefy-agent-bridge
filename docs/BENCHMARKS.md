# Benchmarks — reliability & latency (PRD-2)

Public, reproducible numbers for the **inventory** golden scenario across the **Cursor SDK** and **NVIDIA NAT** harnesses. Live runs are **operator-invoked** (needs `.env` with Pipefy + NVIDIA keys); CI stays lint-only.

> **Status:** **Post-fix live run (2026-06-03)** below scores `eval/fixtures/live/inventory.json` after `eval/ground_truth.sh`. Pre-fix table (example fixture) is archived in git history — do not use for D18/D19.

## Run metadata

| Field | Value |
| --- | --- |
| **Run date (UTC)** | `2026-06-03` |
| **`pipefy/ai-toolkit` tag** | `v0.2.0-beta.2` _(Makefile `PIPEFY_TOOLKIT_REF`; confirm with `pipefy --version`)_ |
| **`cursor-sdk`** | `0.1.6` _(Makefile `CURSOR_SDK_VERSION`)_ |
| **`nvidia-nat` (+ profiler extra)** | `1.7.0` _(Makefile `NVIDIA_NAT_VERSION`; profiler via `nvidia-nat-profiler`)_ |
| **NIM model (NAT)** | `meta/llama-3.1-8b-instruct` _(default; override with `EVAL_ARGS=--model …` or `NIM_MODEL=…`)_ |
| **Golden scenario** | `inventory` (`eval/golden.yaml` → `example_baseline` fixture; **scoring** uses `eval/fixtures/live/inventory.json`) |
| **Runner settings (NAT)** | `--runs 3`, `--retries 3`, `--harness nat` |
| **Runner settings (Cursor)** | `--runs 1`, `--retries 3`, `--harness cursor` _(smoke row; re-run with `--runs 5` for parity)_ |

Optional second row for **70b** (when NVIDIA tier allows): `meta/llama-3.1-70b-instruct` via `--model` / `NIM_MODEL` — **not measured** in the 2026-06-03 close-out (operator optional).

## Reliability & latency (per harness)

Measured with `eval/run_eval.py` scoring via `eval/compare.py` against the live baseline refreshed by `eval/ground_truth.sh`.

| Harness | N | First-attempt % | With-retries % | Median latency (s) | P90 latency (s) |
| --- | ---: | ---: | ---: | ---: | ---: |
| nat | 3 | 33.3 | 66.7 | 35.92 | 205.60 |

_Pre-fix (invalid baseline): cursor 1 / 0% / 0% / 26.45 / 38.17; nat 3 / 0% / 0% / 19.86 / 31.27 — scored against `eval/fixtures/example/inventory.json`._

**Metric definitions**

- **First-attempt %:** share of episodes that passed on attempt 1 (`--retries` window still applies to episode structure, but only attempt 1 counts).
- **With-retries %:** share of episodes where any attempt in `1..retries` passed (runner stops early on first pass).
- **Median / P90 latency (s):** wall-clock **per episode** — sum of attempt latencies until pass or retries exhausted (post-fix runner; pre-fix table used per-attempt aggregation).

**Reproduce command (NAT, 8b):**

```bash
make eval EVAL_ARGS="--scenario inventory --harness nat --runs 3 --retries 3 --json --emit-markdown"
```

**Reproduce command (Cursor smoke):**

```bash
make eval EVAL_ARGS="--scenario inventory --harness cursor --runs 1 --retries 3 --json --emit-markdown"
```

## NAT profiler summary (shape reference)

Live profiling uses `make profile-nat` → `eval/profiles/<timestamp>.json` (gitignored). The committed synthetic sample [`eval/fixtures/example/profile.json`](../eval/fixtures/example/profile.json) documents the **normalized** summary shape used in reports:

| Section | Fields (illustrative) |
| --- | --- |
| `run` | `scenario`, `harness`, `workflow_config`, `model`, `captured_at` |
| `summary` | `total_duration_s`, `agent_iteration_count`, `trace_step_count`, `tool_call_count`, `llm_invocation_count` |
| `workflow_runtime` | `mean_s`, `p50_s`, `p90_s`, `confidence_interval_90_s` |
| `iterations[]` | per-step `kind` (`llm` \| `tool`), `duration_ms`, optional `name` / `label` |
| `nat_profiler_artifacts` | pointers to NAT-native files under the profile output dir |

**Example (synthetic fixture, not a live measurement):** total wall time **18.42 s**, **4** agent iterations, **7** trace steps, **4** tool calls, **3** LLM calls; dominant steps include `search_pipes` (~890 ms) and repeated `get_cards` (~580–620 ms).

## Reproduce

Prerequisites: `cp .env.example .env`, fill Pipefy service account + `DEMO_ORG_ID`, `NVIDIA_API_KEY`, `CURSOR_API_KEY`; `make doctor`; install harness deps as needed (`make install-cursor-demo`, `make install-nat-demo`).

### Reliability runner (golden eval)

Default (both harnesses, 5 episodes, 8b NAT via env default):

```bash
make eval
```

Explicit flags (matches `eval/run_eval.py`):

```bash
make eval EVAL_ARGS="--scenario inventory --harness both --runs 5 --retries 3"
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
NIM_MODEL=meta/llama-3.1-70b-instruct make profile-nat SCENARIO=inventory
```

Profiler output lands under `eval/profiles/` (ignored by git). Compare shape to [`eval/fixtures/example/profile.json`](../eval/fixtures/example/profile.json).

---

## Operator: run and paste (refresh)

When credentials or org data change, re-run and replace the **Run metadata** date and **Reliability & latency** table.

1. Refresh ground truth baseline (read-only Pipefy pull):

   ```bash
   ./eval/ground_truth.sh inventory
   ```

   Ensures scoring uses current org data while golden `expect` facts stay fixture-based.

2. Run evaluation (8b default, both harnesses):

   ```bash
   make eval EVAL_ARGS="--scenario inventory --harness both --runs 5 --retries 3 --json --emit-markdown"
   ```

   Copy the printed Markdown table into **Reliability & latency** above; set **Run date** to the UTC date of the run.

3. _(Optional, tier permitting)_ Repeat with 70b:

   ```bash
   make eval EVAL_ARGS="--scenario inventory --harness nat --runs 5 --model meta/llama-3.1-70b-instruct --emit-markdown"
   ```

4. Capture profiler bundle:

   ```bash
   make profile-nat SCENARIO=inventory
   ```

   Summarize `summary` / `iterations` from the newest `eval/profiles/*.json` in **NAT profiler summary** (do not commit live profile JSON).

**Do not** paste organization IDs, tokens, or raw profile paths containing secrets into this document.
