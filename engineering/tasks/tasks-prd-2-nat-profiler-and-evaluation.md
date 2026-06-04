# Tasks — PRD-2: NAT Profiler & Evaluation

**PRD status:** **Done** (2026-06-03) — all tasks 1.0–6.0 complete; proceed to PRD-3.

**PRD:** [product/prd/prd-2-nat-profiler-and-evaluation.md](../../product/prd/prd-2-nat-profiler-and-evaluation.md)
**Architecture:** [docs/ARCHITECTURE_AND_IMPLEMENTATION_PLAN.md](../../docs/ARCHITECTURE_AND_IMPLEMENTATION_PLAN.md) (Phase 5; §17 evaluation)
**Baseline:** PRD-1 (shipped) — reuses `eval/compare.py`, `eval/ground_truth.sh`, `scripts/extract_nat_answer.py`.
**Roadmap:** [product/prd/README.md](../../product/prd/README.md)

> Constraints carried from PRD-1: CI stays **lint-only** (no external calls); evaluation is **operator-invoked**; read-only; keep 8b default (70b opt-in, D18/D19). Execute one sub-task at a time (see [.cursor/commands/development.md](../../.cursor/commands/development.md)).
> Critical path: **1.0 → 2.0 → 3.0 → 4.0 → 5.0** (3.0 may proceed in parallel with 2.0 once 1.0 is done).

## Relevant Files

- `eval/golden.yaml` — `example_baseline` + `expect` (fixture validation); scoring uses live baseline via `ground_truth.sh`.
- `eval/golden_loader.py`, `eval/golden_expect.py` — load golden + validate `expect` against example fixture.
- `eval/ground_truth_refresh.py` — `refresh_ground_truth()`, `scoring_baseline_path()` for live scoring.
- `eval/eval_summary.py` — `summarize()`, episode latency percentiles, Markdown table formatters.
- `eval/inventory_prompt.py` — shared inventory MCP hints (smoke + profiler).
- `eval/run_eval.py` — runner: live baseline refresh, harness loop, `--skip-ground-truth` for offline debug.
- `eval/fixtures/example/profile.json` — committed synthetic NAT profiler sample (normalized summary; live shape in `eval/profiles/*.json`).
- `configs/pipefy_nat_workflow_profile.yml` — opt-in NAT workflow + `eval.general.profiler` (not used by `make demo-nat`).
- `eval/profile_nat.sh` — operator entry: `nat eval` + bundle → `eval/profiles/<timestamp>.json`.
- `eval/bundle_nat_profile.py`, `eval/nat_inventory_eval_prompt.py` — dataset + artifact bundling helpers.
- `eval/datasets/inventory_profile.json` — static fallback row for profile config.
- `docs/BENCHMARKS.md` — reliability/latency report (dated live run 2026-06-03; operator refresh section).
- `Makefile` — add `eval` and `profile-nat` targets (modify existing).
- `.gitignore` — ignore `eval/profiles/` live profiler output (modify existing).
- `tests/test_bundle_nat_profile.py` — offline bundle + prompt tests (create new).
- `eval/compare.py`, `scripts/extract_nat_answer.py`, `eval/ground_truth.sh` — reused (no rewrite).
- `tests/test_golden_loader.py` — unit tests for golden schema validation (offline) (create new).
- `tests/test_run_eval.py` — unit tests for the runner's aggregation/summary logic (offline) (shipped).

### Notes

- Reliability metric MUST separate **first-attempt** vs **with-retries** pass rate (FR-7).
- Runner MUST support `8b` vs `70b` override without code changes (FR-6) to inform D18.
- Only aggregation/loader logic is offline-unit-testable; live runs need NIM/Pipefy creds and stay operator-invoked.
- Run tests with `uv run pytest tests/ -v`.

## Tasks

- [x] 1.0 **Golden evaluation set & committed fixtures** _(FR-1, FR-3 example; enables the runner)_

  **Trigger:** Start of PRD-2 build.
  **Enables:** 2.0 (runner consumes `golden.yaml`) and 4.0 (benchmarks reference fixtures).
  **Depends on:** PRD-1 `eval/fixtures/example/inventory.json` and `eval/compare.py` semantics (D12).
  **Acceptance criteria:** `eval/golden.yaml` defines `inventory` (required) with expected facts tied to a committed example baseline; `eval/golden_loader.py` validates it; a synthetic profiler example exists; `uv run pytest tests/test_golden_loader.py` green; nothing references live org data.

  - [x] 1.1 Define the golden set schema and `inventory` entry
    - **File**: `eval/golden.yaml` (create new)
    - **What**: A list of scenarios; each has `scenario`, `baseline` (path to a committed `eval/fixtures/example/*.json`), and `expect` (e.g. `min_pipes`, `pipe_name_substrings`) consistent with `eval/compare.py` facts (count + name substrings, D12). Include `inventory` (required); leave `stale_cards`/`summary` commented as optional.
    - **Why**: FR-1 — a versioned, fact-based answer key the runner scores against.
    - **Pattern**: Mirror the fields `eval/compare.py` already extracts; reference the existing `eval/fixtures/example/inventory.json`.
    - **Verify**: `uv run python -c "import yaml; yaml.safe_load(open('eval/golden.yaml'))"` parses; `inventory` entry points to an existing fixture.
    - **Integration**: Consumed by `eval/golden_loader.py` (1.2) and `eval/run_eval.py` (2.x).
  - [x] 1.2 Implement `eval/golden_loader.py` (load + validate)
    - **File**: `eval/golden_loader.py` (create new), `tests/test_golden_loader.py` (create new)
    - **What**: Pure function `load_golden(path) -> list[GoldenCase]` that validates required keys, that each `baseline` file exists, and that `expect` has at least one fact; raises a clear error (with the offending scenario + missing field) otherwise. Tests cover: valid file loads; missing `baseline` raises; empty `expect` raises.
    - **Why**: FR-1 — fail fast with actionable errors; keep it offline-testable.
    - **Pattern**: Plain dataclasses; error messages include the offending value and expected shape (repo clean-code rule).
    - **Verify**: `uv run pytest tests/test_golden_loader.py -v` passes.
  - [x] 1.3 Commit a synthetic profiler example fixture
    - **File**: `eval/fixtures/example/profile.json` (create new)
    - **What**: Small synthetic NAT-profiler-shaped JSON (end-to-end + per-step timing fields) used as a committed sample and by `docs/BENCHMARKS.md`. No real org data.
    - **Why**: FR-3 — public-repo-safe example so readers see the profile shape without running NAT.
    - **Pattern**: Match the real profiler output shape confirmed in 3.1 (update if it differs).
    - **Verify**: File parses as JSON; contains timing fields referenced by the report (4.1).

- [x] 2.0 **Evaluation runner with reliability metrics** _(FR-2, FR-6, FR-7; the core deliverable)_

  **Trigger:** `make eval` (operator-invoked).
  **Enables:** 4.0 (benchmarks consume runner output).
  **Depends on:** 1.0; reuses `eval/compare.py`, `scripts/extract_nat_answer.py`, `eval/ground_truth.sh`.
  **Acceptance criteria:** `make eval` runs each scenario N times per harness (configurable, small default), reports **first-attempt vs with-retries** pass rate + median/p90 latency, supports `8b`/`70b` override without code changes, and its aggregation logic is covered by offline unit tests.

  - [x] 2.1 Create `eval/run_eval.py` CLI skeleton
    - **File**: `eval/run_eval.py` (create new)
    - **What**: Argparse CLI: `--scenario` (default `inventory`), `--harness` (`cursor`|`nat`|`both`, default `both`), `--runs N` (default 5), `--model` (passes `NIM_MODEL` for NAT), `--retries` (default 3 for the with-retries metric). Load cases via `eval/golden_loader.py`.
    - **Why**: FR-2/FR-6 — single entry point; model override via flag (no code change).
    - **Pattern**: Reuse `eval/ground_truth.sh` to refresh the live baseline before scoring.
    - **Verify**: `uv run python eval/run_eval.py --help` lists all flags.
  - [x] 2.2 Implement per-run execution + scoring
    - **File**: `eval/run_eval.py` (modify)
    - **What**: For each run: invoke the harness (`make demo-cursor`/`make demo-nat` or the scripts) capturing stdout+stderr and wall-clock latency; extract the NAT answer via `scripts/extract_nat_answer.py`; score via `eval/compare.py` against the baseline. Record per-run `{harness, attempt, passed, latency_s}`.
    - **Why**: FR-2 — reuse the shipped extraction/compare, don't reimplement.
    - **Pattern**: `subprocess.run` with timeout; set `NIM_MODEL` in env for NAT when `--model` given.
    - **Verify**: A dry `--runs 1` against a stubbed/cached answer records one result row (manual smoke; live needs creds).
    - **Integration**: Emits a results list consumed by the aggregator (2.3) and the report (4.x).
  - [x] 2.3 Implement aggregation (first-attempt vs with-retries + latency)
    - **File**: `eval/run_eval.py` (modify), `tests/test_run_eval.py` (create new)
    - **What**: Pure function `summarize(results, retries) -> Summary` computing per-harness: first-attempt pass rate, with-retries pass rate (a scenario "passes with retries" if any of its first `retries` attempts passed), median + p90 latency, N. Print a compact table + emit JSON. Tests cover: all-pass, all-fail, mixed (first fails second passes → with-retries pass, first-attempt fail), latency percentiles.
    - **Why**: FR-7 — the headline reliability numbers; offline-testable.
    - **Pattern**: Keep `summarize` pure (input list → Summary) so tests need no network.
    - **Verify**: `uv run pytest tests/test_run_eval.py -v` passes.
  - [x] 2.4 Add `make eval` target
    - **File**: `Makefile` (modify existing)
    - **What**: `eval` target loads `.env` and runs `uv run python eval/run_eval.py $(EVAL_ARGS)`; document `EVAL_ARGS` (e.g. `--runs 5 --model meta/llama-3.1-70b-instruct`).
    - **Why**: FR-2 — one-command operator entry; consistent with existing target style.
    - **Verify**: `make eval EVAL_ARGS="--help"` prints the runner help.

- [x] 3.0 **NAT profiler capture** _(FR-3)_

  **Trigger:** Runner (or a dedicated profile command) invokes `nat run` with profiling enabled.
  **Enables:** 4.0 (timing/iteration data in the report).
  **Depends on:** PRD-1 NAT workflow (`configs/pipefy_nat_workflow.yml`).
  **Acceptance criteria:** A `nat run` for `inventory` produces profiler timing/iteration JSON under a gitignored `eval/profiles/`; `.gitignore` ignores it; the committed example (1.3) matches the real shape.

  - [x] 3.1 Confirm NAT profiler config/flags and enable it
    - **File**: `configs/pipefy_nat_workflow.yml` (modify) or a sibling profile config (create new)
    - **What**: Per NAT eval/profiler docs, enable profiling for the `inventory` run (config block or CLI flag). Confirm the exact knob against [NeMo Agent Toolkit](https://docs.nvidia.com/nemo/agent-toolkit/latest/index.html); do not change runtime behavior of the default `make demo-nat`.
    - **Why**: FR-3 — capture timing/iteration data without altering the demo path.
    - **Pattern**: Prefer a separate profile config or an opt-in flag so the default tour is unaffected.
    - **Verify**: A profiled `nat run` writes a profiler artifact (operator-run; needs `NVIDIA_API_KEY`).
  - [x] 3.2 Persist profiles to a gitignored path + ignore it
    - **File**: `eval/run_eval.py` or `eval/profile_nat.sh` (create/modify), `.gitignore` (modify existing)
    - **What**: Write profiler JSON to `eval/profiles/<timestamp>.json`; add `eval/profiles/` to `.gitignore`.
    - **Why**: FR-3 / D13 — live profiles may carry org-specific data; keep them out of git.
    - **Verify**: After a profiled run, the JSON lands under `eval/profiles/`; `git check-ignore eval/profiles/x.json` succeeds.

- [x] 4.0 **Benchmarks report** _(FR-4)_

  **Trigger:** After a runner + profiler pass.
  **Enables:** Transparent reliability story for cloners/reviewers.
  **Depends on:** 2.0 and 3.0.
  **Acceptance criteria:** `docs/BENCHMARKS.md` records the latest run (date, toolkit/model versions, first-attempt vs with-retries pass rate, latency) and the exact reproduce command; no secrets/live IDs.

  - [x] 4.1 Create the `docs/BENCHMARKS.md` template
    - **File**: `docs/BENCHMARKS.md` (create new)
    - **What**: Sections: run metadata (date, `pipefy/ai-toolkit` tag, `nvidia-nat`/`cursor-sdk` versions, NIM model), results table (per harness: first-attempt %, with-retries %, median/p90 latency, N), profiler summary (from `eval/fixtures/example/profile.json` shape), and the exact reproduce command (`make eval EVAL_ARGS=...`).
    - **Why**: FR-4 — the public, dated reliability artifact.
    - **Pattern**: Use synthetic/example numbers as placeholders until a real run fills them; never paste org IDs.
    - **Verify**: Renders as valid markdown; reproduce command matches the `make eval` interface (2.4).
  - [x] 4.2 Populate with a real run + optional snippet emit
    - **File**: `docs/BENCHMARKS.md` (modify), `eval/run_eval.py` (optional `--emit-markdown`)
    - **What**: Run `make eval` for `inventory` (8b; and 70b if D18 tier allows) and paste the dated summary; optionally add `--emit-markdown` to `run_eval.py` to print a ready-to-paste table.
    - **Why**: FR-4 — real numbers; reduces manual transcription.
    - **Verify**: `docs/BENCHMARKS.md` shows a dated result and the command that produced it (operator-run; needs creds).

- [x] 5.0 **Close-out: reconcile artifacts, decisions & commit** _(planning hygiene, mirrors PRD-1 FR-28)_

  **Trigger:** PRD-2 deliverables green.
  **Enables:** Trustworthy baseline for PRD-3/PRD-4 decisions.
  **Depends on:** 4.0.
  **Acceptance criteria:** ARCHITECTURE §17/Phase 5 boxes updated; `product/prd/README.md` marks PRD-2 status; `docs/OPEN_DECISIONS.md` records the measured 8b-vs-70b outcome (informs D18/D19); `ruff` + offline tests green; an atomic local commit created (no remote push).

  - [x] 5.1 Reconcile ARCHITECTURE Phase 5 / §17
    - **File**: `docs/ARCHITECTURE_AND_IMPLEMENTATION_PLAN.md` (modify existing)
    - **What**: Tick Phase 5 boxes/exit criteria delivered; link `docs/BENCHMARKS.md` from §17.
    - **Why**: FR — backbone stays accurate.
    - **Verify**: §17/Phase 5 reflect the shipped eval/profiler.
  - [x] 5.2 Update the PRD roadmap index
    - **File**: `product/prd/README.md` (modify existing)
    - **What**: Move PRD-2 status to In progress/Done; add a deltas note if scope shifted.
    - **Verify**: PRD-2 row shows the new status.
  - [x] 5.3 Record the 8b-vs-70b measured outcome
    - **File**: `docs/OPEN_DECISIONS.md` (modify existing), `docs/LEARNINGS.md` (modify existing)
    - **What**: With real `make eval` numbers, resolve/annotate D18 (70b tier value-for-barrier) and confirm or revisit D19 (reliability contract).
    - **Why**: FR — close the long-open `70b` question with data, not guesswork.
    - **Verify**: D18/D19 reference the benchmark numbers/date.
  - [x] 5.4 Lint, test, and commit
    - **File**: _repository_ (no file)
    - **What**: `uv run ruff check .` and `uv run pytest tests/ -v` green; create one atomic Conventional Commit (e.g. `feat(eval): NAT profiler + reliability eval runner`). Do **not** push.
    - **Why**: FR-5 + repo hygiene; keep CI lint-only.
    - **Verify**: `git log --oneline -1` shows the commit; `git status` clean; no push performed.

## Post-ship quality fixes (thermo-nuclear review, 2026-06)

**Root cause:** `run_eval` scored agent answers against `eval/fixtures/example/inventory.json` while agents answered about the live org; `golden.yaml` `expect` was loaded but never validated or used for scoring. Docs claimed `ground_truth.sh` + live baseline.

**Decisions (post-fix):**

- Scoring path: `ground_truth.sh` → `eval/fixtures/live/<scenario>.json` (once per `make eval`, not per attempt).
- `golden.yaml`: `example_baseline` + `expect` validate the committed fixture only.
- Latency: median/p90 over **episode** wall-clock (sum of attempts until pass or retries exhausted).
- Profiler bundle: lean default (paths + summary); `EMBED_ARTIFACTS=1` or `--embed-artifacts` for full inline JSON.

**Invalidated metrics:** [docs/BENCHMARKS.md](../../docs/BENCHMARKS.md) table dated **2026-06-03** (pre-fix) — do not use for D18/D19 until operator re-run.

- [x] **6.0** Parent — quality fix track

  - [x] **6.1** Live scoring + `ground_truth_refresh.py` + `--skip-ground-truth` — verify: `uv run pytest tests/test_ground_truth_refresh.py -v`
  - [x] **6.2** `example_baseline` / `expect` validation (`golden_expect.py`) — verify: `tests/test_golden_loader.py`
  - [x] **6.3** `load_baseline` in compare; `inventory_prompt.py`; smoke uses `--print-prompt` — verify: `tests/test_inventory_prompt.py`
  - [x] **6.4** `eval_summary.py` + episode latency — verify: `tests/test_run_eval.py`
  - [x] **6.5** Bundle lean default + `--embed-artifacts` — verify: `tests/test_bundle_nat_profile.py`
  - [x] **6.6** Docs: BENCHMARKS, OPEN_DECISIONS, LEARNINGS note pre-fix invalidation — re-benchmark **2026-06-03** NAT 3×3 post-fix (33.3% / 66.7% / med 35.92s)
  - [x] **6.7** This section + Relevant Files updated

**Optional (out of scope):** `--parallel-harnesses`; `stale_cards`/`summary` in runner; CI gating on live eval.
