# Open decisions

Decisions that are **intentionally deferred** in the architecture plan. Resolve them during implementation and update this file (move rows to “Resolved” with date).

> **MVP (Phases 0–4, 2026-06-02):** Implementation decisions **D1–D14** are closed. No build-time items remain in the phase gates below. Stretch choices **D15–D17** stay in “Nice to have” until PRD-2/3/4.

> Maintainer-only context (goals, audience, timeline) belongs in `private/CONTEXT.md` (gitignored)—not in this file.

---

## Must decide before Phase 1

> **Shipped.** D1–D5 resolved — see **Resolved** (D2/D4 updated with frozen tag and tool count).

---

## Must decide before Phase 2 (Cursor)

> **Shipped.** D6–D8 resolved — see **Resolved** (D20 records demo dependency pins).

---

## Must decide before Phase 3 (NVIDIA NAT)

> **Shipped.** D9–D11 resolved — see **Resolved** (D18 closes the `70b` tier question for MVP).

---

## Must decide before Phase 4 (tour / eval)

> **Shipped.** D12–D14 resolved — see **Resolved**.

---

## Nice to have (stretch)

| ID | Decision | Notes |
|----|----------|-------|
| D15 | Cursor Cloud agent demo | Requires GitHub repo + SCM connection |
| D16 | GPU embeddings backend | FAISS CPU fallback vs cuVS GPU |
| D17 | Publish workflow as MCP via `nat mcp serve` | Second harness exposure |

---

## Resolved

| ID | Decision | Resolution | Date |
|----|----------|------------|------|
| R1 | Primary artifact: video vs runnable | **Runnable tour** (`TRY_IT_YOURSELF.md`); recording optional | 2026-06-02 |
| R2 | Process-specific framing in public README | **Removed**; maintainer context only in `private/CONTEXT.md` (gitignored) | 2026-06-02 |
| R3 | Dual harness in one repo | **Yes** — MCP shared; separate entrypoints | 2026-06-02 |
| D1 | License | **MIT** — see `LICENSE` and README | 2026-06-02 |
| D2 | pipefy/ai-toolkit pin | **`v0.2.0-beta.2`** — `PIPEFY_TOOLKIT_REF` in `Makefile`, `pipefy_toolkit_ref` in `configs/tool_allowlist.yml`, `make install-pipefy-tools` | 2026-06-02 |
| D3 | Git remote URL | **Keep `<your-org>` as a placeholder** — each operator forks/clones into their own GitHub org/account; no hardcoded URL in public docs. (Maintainer Pipefy demo org is set locally via `DEMO_ORG_ID`, not committed.) | 2026-06-02 |
| D4 | MVP MCP tool allowlist | **12 tools** in `configs/tool_allowlist.yml`, names verified against `pipefy-mcp-server` @ **D2** tag via `nat mcp client tool list` | 2026-06-02 |
| D5 | Default tour scenario | **`inventory`** — read-only, org-wide discovery | 2026-06-02 |
| D6 | Cursor model ID | **`composer-2.5`** in `demos/01_cursor_pipefy_ops.py` | 2026-06-02 |
| D7 | Python env manager | **`uv` only** — aligns with pipefy/ai-toolkit (`uv` workspace); no `pip` path documented | 2026-06-02 |
| D8 | Load `.env` | **`python-dotenv`** in demo deps | 2026-06-02 |
| D9 | NIM model (MVP default) | **`meta/llama-3.1-8b-instruct`** in `configs/pipefy_nat_workflow.yml` for the tour | 2026-06-02 |
| D10 | NAT `max_iterations` | **`22`** for shipped inventory workflow (supersedes MVP default `8`; see [LEARNINGS.md](LEARNINGS.md)) | 2026-06-02 |
| D11 | Makefile target naming | **`demo-nat` only** (matches `demo-cursor`); no `nat-demo` alias; CLI baselines via `eval/ground_truth.sh` (no `eval-baseline` target) | 2026-06-02 |
| D12 | Eval strictness | **Count + pipe-name substring match** in `eval/compare.py` (no exact-ID match for MVP) | 2026-06-02 |
| D13 | Sensitive fixtures | **`eval/fixtures/example/` committed** (synthetic), **`eval/fixtures/live/` gitignored** | 2026-06-02 |
| D14 | Recording doc | **No `DEMO_RECORDING.md`** — recording kept as a single optional paragraph in `TRY_IT_YOURSELF.md` (recording is a low-priority secondary artifact) | 2026-06-02 |
| D18 | NIM `70b` API tier check | **Not validated for MVP** — `inventory` gate uses **8b** only. Operators may set `model_name: meta/llama-3.1-70b-instruct` in the workflow YAML if their [NVIDIA Build](https://build.nvidia.com/) tier allows it; no automated check in `make doctor` | 2026-06-02 |
| D20 | Demo harness dependency pins | **`cursor-sdk==0.1.6`**, **`python-dotenv==1.2.2`**, **`nvidia-nat[langchain,mcp]==1.7.0`** in `Makefile` install targets | 2026-06-02 |

---

## How to close a decision

1. Pick an option and implement.
2. Update ARCHITECTURE plan if the decision changes structure.
3. Move the row to **Resolved** with date and short rationale.
