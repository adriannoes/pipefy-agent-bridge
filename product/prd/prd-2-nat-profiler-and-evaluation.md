# PRD-2: NAT Profiler & Evaluation

**Status:** Draft for sign-off
**Version:** 0.1
**Date:** 2026-06-03
**Owner:** Repository maintainer
**Related documents:**
- [product/prd/prd-pipefy-agent-bridge-mvp.md](prd-pipefy-agent-bridge-mvp.md) (PRD-1, shipped — baseline)
- [docs/ARCHITECTURE_AND_IMPLEMENTATION_PLAN.md](../../docs/ARCHITECTURE_AND_IMPLEMENTATION_PLAN.md) (Phase 5; §17 evaluation strategy)
- [docs/LEARNINGS.md](../../docs/LEARNINGS.md) (NAT 8b flakiness, compare robustness, tour retries)
- [docs/OPEN_DECISIONS.md](../../docs/OPEN_DECISIONS.md) (D10 `max_iterations=22`, D18 `70b` tier)

> Scope note: PRD-2 covers **architecture Phase 5 (stretch)** and builds on the shipped MVP. It depends on a green MVP tour and does **not** include GPU (Phase 7) or Cloud (Phase 6).

---

## 1. Introduction / Overview

The MVP proved the dual-harness bridge works for the `inventory` scenario, but `docs/LEARNINGS.md` documents a concrete reliability gap: the **NVIDIA NAT + NIM 8b path is flaky** (observed 1/3–3/3 first-attempt success on a busy org), today masked by retries in `scripts/tour.sh`. PRD-2 turns that anecdotal observation into **measured, repeatable evaluation**: enable the NAT profiler, add a small golden evaluation set referencing CLI fixtures, and publish a reproducible reliability/latency report.

The deliverable answers, with evidence: "How often, how fast, and how correctly does each harness answer the canonical scenarios?" — and gives a number we can improve against (e.g. NAT first-attempt pass rate).

---

## 2. Goals

1. Make harness **reliability** a measured metric, not an anecdote (first-attempt pass rate over N runs per scenario/harness).
2. Capture **latency/iteration** profiles for `nat run` via the NAT profiler.
3. Provide a small, versioned **golden evaluation set** that scores agent answers against CLI ground truth (reusing `eval/compare.py` logic).
4. Publish a reproducible `docs/BENCHMARKS.md` so the reliability story is transparent to anyone cloning the repo.
5. Keep CI offline (no external calls); evaluation runs are operator-invoked, not CI-gated.

---

## 3. User Stories

- **As a maintainer**, I want a one-command eval that runs each scenario N times per harness and reports pass rate + median latency, so that I can quantify reliability and detect regressions.
- **As a reviewer**, I want a `docs/BENCHMARKS.md` with dated numbers and the exact command to reproduce them, so that I trust the reliability claims.
- **As a contributor tuning NAT**, I want the profiler output and golden scores side by side, so that I can tell whether a workflow change (model, `max_iterations`, tool subset) actually helped.

---

## 4. Functional Requirements

1. The repo MUST provide `eval/golden.yaml` with golden Q&A entries per scenario (`inventory` required; `stale_cards`/`summary` optional), each referencing a committed `eval/fixtures/example/*.json` baseline and the expected facts (counts, pipe-name substrings) consistent with D12.
2. The repo MUST provide an evaluation runner (e.g. `make eval` / `eval/run_eval.py`) that runs each scenario N times per harness (N configurable, default small), records pass/fail via `eval/compare.py`, and emits a summary (pass rate, attempts, median/p90 latency).
3. The runner MUST capture the **NAT profiler** output for `nat run` (timing/iteration JSON) and store it under a gitignored path (e.g. `eval/profiles/`), with a synthetic example committed under `eval/fixtures/example/`.
4. The repo MUST provide `docs/BENCHMARKS.md` summarizing the latest run (date, toolkit/model versions, pass rate, latency) and the exact reproduce command.
5. Evaluation MUST be **operator-invoked**; CI MUST remain lint-only (no Pipefy/NIM/Cursor calls), per PRD-1 FR-25.
6. The runner MUST support comparing `8b` vs `70b` (model override) without code changes, to inform D18.
7. Reliability reporting MUST distinguish **first-attempt** pass rate from **with-retries** pass rate (the MVP tour uses retries).

---

## 5. Non-Goals (Out of Scope)

1. GPU embeddings / semantic search (PRD-4 / Phase 7).
2. Cursor Cloud agents (PRD-3 / Phase 6).
3. Write/mutation scenarios.
4. LLM-as-judge scoring (keep fact-based comparison from D12).
5. Gating CI on live evaluation (stays operator-invoked).
6. Fine-tuning or RL (NAT roadmap, not this repo).

---

## 6. Technical Considerations

- **Profiler:** use the NAT evaluation/profiler subsystem ([NeMo Agent Toolkit](https://docs.nvidia.com/nemo/agent-toolkit/latest/index.html) eval docs); confirm the exact config/flags at implementation time.
- **Reuse:** build on `eval/compare.py`, `scripts/extract_nat_answer.py`, and `eval/ground_truth.sh` from the MVP; do not reimplement fact extraction.
- **Reliability tuning interplay:** any NAT-stabilization work (prompt/tool-subset/model tuning) should be measured by this PRD's runner; PRD-2 provides the yardstick, the tuning is the experiment.
- **Fixtures:** synthetic examples committed under `eval/fixtures/example/`; live profiles/snapshots gitignored (`eval/fixtures/live/`, `eval/profiles/`).
- **Security:** unchanged from MVP (service account, sandbox, no secrets committed).

---

## 7. Success Metrics

1. `make eval` (or documented runner) produces a pass-rate + latency summary for `inventory` on both harnesses in one command.
2. `docs/BENCHMARKS.md` exists with a dated, reproducible result and the exact command.
3. The runner reports first-attempt vs with-retries NAT pass rate separately.
4. CI remains lint-only and green.

---

## 8. Open Questions

1. **N (runs per scenario)** default for the reliability metric (e.g. 5 vs 10) — trade-off between signal and NIM cost/time.
2. **Profiler output shape** and whether NAT exposes per-tool timing we can chart, or only end-to-end.
3. **Reliability target** to declare "good enough" (e.g. ≥80% first-attempt on `inventory` with 8b) — or do we accept retries as the contract and target with-retries ~100%?
4. **70b** inclusion: run the comparison only if D18 (key tier) is resolved.

---

## 9. Dependencies & Sequencing

- **Depends on:** shipped MVP (PRD-1) — reuses `eval/`, `scripts/`, `configs/`.
- **Precursor (optional, parallel):** a tactical NAT-stabilization pass (prompt/tool-subset/model tuning) may run before or alongside this PRD; PRD-2 measures whether it helped.
- **Independent of:** PRD-3 (Cloud), PRD-4 (GPU).
