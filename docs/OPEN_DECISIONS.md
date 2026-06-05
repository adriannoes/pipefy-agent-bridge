# Open decisions

Record of **resolved** architecture choices and **optional** items still open. When you change a default or contract, update this file and [ARCHITECTURE_AND_IMPLEMENTATION_PLAN.md](ARCHITECTURE_AND_IMPLEMENTATION_PLAN.md) if layout or behavior shifts.

> **Core tour (Phases 0–4, 2026-06-02):** Decisions **D1–D14** are closed. **D15** resolved with Cursor Cloud (2026-06-04); **D16** resolved with GPU semantic search (2026-06-04). Optional **D17** remains below.

---

## Optional (not implemented)

| ID | Decision | Notes |
|----|----------|-------|
| D17 | Publish workflow as MCP via `nat mcp serve` | Second harness exposure |

---

## Resolved

| ID | Decision | Resolution | Date |
|----|----------|------------|------|
| R1 | Primary artifact: video vs runnable | **Runnable tour** (`TRY_IT_YOURSELF.md`); recording optional | 2026-06-02 |
| R2 | Public README tone | **Operator-focused** — no internal process framing in README or docs index | 2026-06-02 |
| R3 | Dual harness in one repo | **Yes** — MCP shared; separate entrypoints | 2026-06-02 |
| D1 | License | **MIT** — see `LICENSE` and README | 2026-06-02 |
| D2 | pipefy/ai-toolkit pin | **`v0.2.0-beta.2`** — `PIPEFY_TOOLKIT_REF` in `Makefile`, `pipefy_toolkit_ref` in `configs/tool_allowlist.yml`, `make install-pipefy-tools` | 2026-06-02 |
| D3 | Git remote URL | **Keep `<your-org>` as a placeholder** — each operator forks/clones into their own GitHub org/account; no hardcoded URL in public docs. (Maintainer Pipefy demo org is set locally via `DEMO_ORG_ID`, not committed.) | 2026-06-02 |
| D4 | Core tour MCP tool allowlist | **12 tools** in `configs/tool_allowlist.yml`, names verified against `pipefy-mcp-server` @ **D2** tag via `nat mcp client tool list` | 2026-06-02 |
| D5 | Default tour scenario | **`inventory`** — read-only, org-wide discovery | 2026-06-02 |
| D6 | Cursor model ID | **`composer-2.5`** in `demos/01_cursor_pipefy_ops.py` | 2026-06-02 |
| D7 | Python env manager | **`uv` only** — aligns with pipefy/ai-toolkit (`uv` workspace); no `pip` path documented | 2026-06-02 |
| D8 | Load `.env` | **`python-dotenv`** in demo deps | 2026-06-02 |
| D9 | NIM model (default) | **`meta/llama-3.1-8b-instruct`** in `configs/pipefy_nat_workflow.yml` for the tour | 2026-06-02 |
| D10 | NAT `max_iterations` | **`22`** for shipped inventory workflow (supersedes earlier default `8`; see [LEARNINGS.md](LEARNINGS.md)) | 2026-06-02 |
| D11 | Makefile target naming | **`demo-nat` only** (matches `demo-cursor`); no `nat-demo` alias; CLI baselines via `eval/ground_truth.sh` (no `eval-baseline` target) | 2026-06-02 |
| D12 | Eval strictness | **Count + pipe-name substring match** in `eval/compare.py` (no exact-ID match for the core tour) | 2026-06-02 |
| D13 | Sensitive fixtures | **`eval/fixtures/example/` committed** (synthetic), **`eval/fixtures/live/` gitignored** | 2026-06-02 |
| D14 | Recording doc | **No `DEMO_RECORDING.md`** — recording kept as a single optional paragraph in `TRY_IT_YOURSELF.md` (recording is a low-priority secondary artifact) | 2026-06-02 |
| D18 | NIM `70b` API tier check | **8b default; 70b not measured post-fix.** **Post-fix (2026-06-03):** NAT 8b golden `inventory` — **1/3** first-attempt, **2/3** with-retries ([BENCHMARKS.md](BENCHMARKS.md); live baseline). Pre-fix 0% table invalidated (scored example fixture). Operators may set `70b` via `EVAL_ARGS=--model meta/llama-3.1-70b-instruct` if tier allows. | 2026-06-03 |
| D19 | NAT tour reliability contract | **Act 2 (Cursor) = guaranteed-green in tour; Act 3 (NAT 8b) = best-effort.** **Post-fix golden eval (2026-06-03):** NAT 8b **33%** first-attempt (**1/3**), **67%** with-retries (**2/3**), episode median **35.9 s** / p90 **205.6 s** ([BENCHMARKS.md](BENCHMARKS.md)). Confirms D19: not guaranteed-green on first attempt; keep tour retries. | 2026-06-03 |
| D20 | Demo harness dependency pins | **`cursor-sdk==0.1.6`**, **`python-dotenv==1.2.2`**, **`nvidia-nat[langchain,mcp]==1.7.0`** in `Makefile` install targets | 2026-06-02 |
| D15 | Cursor Cloud agent demo | Repo on **GitHub** + SCM in Cursor; VM provisioning via **`.cursor/environment.json`** → **`scripts/cloud_bootstrap.sh`** (`uv tool install pipefy-mcp-server`); secrets via **`CloudAgentOptions.env_vars`** (+ MCP stdio `env` for `pipefy-mcp-server`); entrypoint **`make demo-cloud`** (`demos/03_cursor_cloud_ops.py`, [`docs/CLOUD.md`](CLOUD.md)) | 2026-06-04 |
| D16 | GPU embeddings backend | **FAISS-CPU default** (`EMBED_BACKEND=cpu`); **GPU opt-in** via `EMBED_BACKEND=gpu` (requires GPU-enabled FAISS; not in CI). NIM default model: **`nvidia/nv-embedqa-e5-v5`** (1024-dim); **`EMBED_PROVIDER=local`** + sentence-transformers when NIM embedding tier unavailable ([`embeddings/README.md`](../embeddings/README.md)). Operator entrypoint: **`make similar`**. | 2026-06-04 |

---

## How to record a new decision

1. Pick an option and implement.
2. Update [ARCHITECTURE_AND_IMPLEMENTATION_PLAN.md](ARCHITECTURE_AND_IMPLEMENTATION_PLAN.md) if the decision changes structure.
3. Add or update a row in **Resolved** (or **Optional**) with date and short rationale.
