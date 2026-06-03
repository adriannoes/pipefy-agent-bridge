# Operational learnings (build log)

Living notes from implementing the MVP harnesses. Use this when debugging `make tour`, extending eval, or tuning NAT/Cursor.

**Related:** [ARCHITECTURE_AND_IMPLEMENTATION_PLAN.md](ARCHITECTURE_AND_IMPLEMENTATION_PLAN.md) · [OPEN_DECISIONS.md](OPEN_DECISIONS.md) · [TRY_IT_YOURSELF.md](TRY_IT_YOURSELF.md)

---

## Pipefy CLI / MCP

### `pipesCount` vs `pipes[]` (truncated inventory)

**What we saw:** `pipefy pipe list --json` can return:

- `pipesCount`: org-wide total (e.g. `274`)
- `pipes[]`: only the first page (e.g. `5` pipes)
- `search_limits.pipes_truncated: true` and/or per-org `pipes_truncated: true`

**Why it matters:** Agents and the Act 1 tour summary describe the **visible page** (5 pipes). If `eval/compare.py` uses `pipesCount` as the baseline count, the **Encore** fact check fails even when the agent answer is correct for the listed pipes.

**What we did:** In `eval/compare.py`, when truncation flags are set (or `pipesCount > len(pipes[])`), baseline `pipe_count` = `len(pipes[])`, not `pipesCount`. Agent answers that cite both “5 pipes” and “274 total” prefer the count that matches the visible list.

**Takeaway for readers:** Treat CLI JSON as “page + metadata,” not always as a full enumeration. For org-wide inventory at scale, expect truncation unless the toolkit adds pagination helpers.

### MCP tool surface vs demo quality

**What we saw:** A broad allowlist (12 tools) is correct for the repo contract, but **NVIDIA `react_agent` + 8b** wanders into `find_cards`, `get_phase_fields`, `get_organization`, etc., burning steps and failing Pydantic validation.

**What we did:** `configs/pipefy_nat_workflow.yml` uses a **2-tool** NAT subset: `search_pipes`, `get_cards` only (still a subset of `tool_allowlist.yml`).

---

## Cursor SDK harness

### Generally reliable for `inventory`

**What we saw:** `make demo-cursor SCENARIO=inventory` usually completes in ~25–90s with multiple MCP tool calls and a markdown table answer. Encore compare passes when the answer lists the same pipe names as the CLI page.

**Caveats:**

- Answers may mention org total (`274`) **and** visible pipes (`5`); compare logic must not treat `274` as the fact-check count when the baseline is truncated.
- Occasional extra tools (`grep`, `shell`) increase latency; not required for inventory.

---

## NVIDIA NeMo Agent Toolkit + NIM

### Default `meta/llama-3.1-8b-instruct` is demo-capable but flaky

**What we saw (repeatable):**

| Symptom | Cause |
|--------|--------|
| `Recursion limit of N reached` | NAT sets `recursion_limit = (max_tool_calls + 1) * 2`. YAML `max_iterations` maps to **`max_tool_calls`**, not a separate knob. Too many bad tool calls exhaust the graph. |
| `search_pipes` with `pipe_name` / missing `organization_id` | 8b invents filters; returns empty `organizations[]`; agent concludes “no pipes”. |
| Malformed tool JSON (`pipe_id` nested in a string) | Native tool calling + weak model; validation errors loop until recursion limit. |
| `get_organization` loops | Wrong org id → permission errors; agent retries until limit. |
| `Final Answer: No pipes found` while log shows pipes | Agent ignored successful `search_pipes`; smoke/tour must reject this. |
| Incomplete Final Answer (1 pipe only) | Agent stops early; Encore compare fails on missing names. |
| Exit code `0` on workflow error | `nat run` may still exit 0; `demos/02_nat_smoke.sh` greps for `ReAct Agent failed`, `Recursion limit`, and requires `Final Answer:`. |

**70b probe (2025-06-02):** `NIM_MODEL=meta/llama-3.1-70b-instruct` can authenticate but still return incomplete inventory; keep **8b** as default until tier + quality are validated.

**Why 8b is still the default (D9):** Sufficient for the thin `inventory` slice when guided; keeps NIM cost/low tier barrier low. **`70b`** is documented as an upgrade path when the maintainer’s key tier allows it (see OPEN_DECISIONS D18).

### Workflow / prompt constraints

| Topic | Learning |
|-------|----------|
| `additional_instructions` | **Do not** put raw `{...}` JSON in YAML — LangChain treats `{organization_id}` as template variables. Use prose (“pass organization_id as integer DEMO_ORG_ID”). |
| `use_native_tool_calling: true` | More reliable structured tool calls than text ReAct parsing for NIM. |
| `raise_on_parsing_failure: false` | Avoids hard crash when the model mixes `Final Answer` and `Action` (still log errors). |
| `parse_agent_response_max_retries: 3` | Helps occasional parse slips. |
| Output streams | Agent steps log to **stderr**; `make tour` / smoke capture **`2>&1`** for `scripts/extract_nat_answer.py`. |
| Console answer extraction | Use the **last** prose `Workflow Result:` block; earlier `---` separators appear in tool logs and break naive regexes. See **`scripts/extract_nat_answer.py`** below. |
| `max_iterations: 22` | Inventory ≈ 1× `search_pipes` + N× `get_cards` (N ≈ visible pipes); NAT `recursion_limit` = 46. Prompt hard cap: **7** tool calls, then Final Answer. **Supersedes** OPEN_DECISIONS D10 (`8`) for the shipped workflow. |

### `scripts/extract_nat_answer.py` (native tool calling)

**What we saw:** With `use_native_tool_calling`, the last `Workflow Result:` line is often JSON (`{"name": "pipefy__…", "parameters": {...}}`), not inventory prose. Feeding that to `eval/compare.py` fails Encore even when a good `Final Answer` exists later in the log.

**What we did:** Skip tool-call-shaped `Workflow Result` blocks; use the last prose block. For `Final Answer:`, match non-greedily until `---` and take the **last non-empty** `Final Answer` (8b emits empty placeholders mid-run).

### macOS `mktemp` in `demos/02_nat_smoke.sh`

**What we saw:** `mktemp …/nat-smoke.XXXXXX.log` is invalid on BSD/macOS (XXXXXX must be the suffix of the basename). The template path was created literally as `nat-smoke.XXXXXX.log`, and every subsequent run failed instantly with `mkstemp: File exists`.

**What we did:** Use `mktemp …/nat-smoke.XXXXXX` (no `.log` after the random suffix).

### Smoke harness gates (inventory)

`demos/02_nat_smoke.sh` now fails on: non-zero exit, workflow/agent errors in the log, missing `Final Answer:`, “no pipes” when the log shows `pipes[]` / `pipesCount`, and **`eval/compare.py`** against `eval/fixtures/live/inventory.json` (requires `./eval/ground_truth.sh inventory` first). Optional: `NIM_MODEL=meta/llama-3.1-70b-instruct` via `--override`.

### Recommended operator flow (NAT)

```bash
make install-nat-demo   # ensures `uv run nat` exists (also: make tour depends on ensure-nat-demo)
make install-cursor-demo # or rely on ensure-cursor-demo when running make tour / demo-cursor
make doctor
./eval/ground_truth.sh inventory
make demo-nat           # may need 2–3 attempts with 8b on busy orgs
```

`scripts/tour.sh` retries demo-nat up to **3** times and runs compare on the extracted answer before Encore.

**Tour deps:** `make tour` runs `ensure-nat-demo` and `ensure-cursor-demo` (auto-install on first run), same pattern as Act 3 / Act 2.

**Flakiness observed (2025-06-02, post-fix):** back-to-back `make demo-nat` on the same org can be **1/3–3/3** in one session (incomplete single-pipe answers vs full 5-pipe inventory). Treat a single failure as normal for 8b; rely on tour retries or `NIM_MODEL=meta/llama-3.1-70b-instruct` when the key tier allows.

---

## Tour / Encore (`eval/compare.py`)

### What “Encore” means

After Acts 1–3, the tour runs **Encore**: `eval/compare.py` checks that each harness answer matches the CLI baseline (**pipe count** + **pipe names** as substrings, case-insensitive). See ARCHITECTURE §16.5.

### Compare robustness

| Behavior | Rationale |
|----------|-----------|
| Truncated baseline → count = listed pipes | Aligns with MCP/CLI page agents actually see. |
| Multiple counts in answer (“5 pipes … 274 total”) | Prefer count matching listed pipes when both appear. |
| No explicit count in answer | Infer from matched pipe names (`effective_pipe_count`). |
| Typo in pipe label (`[Templates]` vs `[Template]`) | Token fallback: ≥2 significant tokens from baseline name must appear in answer. |

---

## Open follow-ups (not blocking docs)

- [ ] Stabilize `make tour` green on first NAT attempt with 8b (retries already wired in `scripts/tour.sh`; `70b` documented as upgrade in README / TRY_IT_YOURSELF / §16.5).
- [ ] Optional: Pipefy toolkit feature request — pagination or `open_cards_count` on `search_pipes` to avoid N× `get_cards` per pipe.

---

**Tour status (docs aligned 2025-06-02):** README, TRY_IT_YOURSELF Step 4, and ARCHITECTURE §16.5 describe `scripts/tour.sh` retries (Cursor ×1, NAT ×3 with compare gate) and Encore truncation rules.

*Last updated: 2025-06-02 — inventory tour / compare / NAT tuning session.*
