# PRD-3: Cursor Cloud Agent

**Status:** Draft for sign-off
**Version:** 0.1
**Date:** 2026-06-04
**Owner:** Repository maintainer
**Related documents:**
- [product/prd/prd-pipefy-agent-bridge-mvp.md](prd-pipefy-agent-bridge-mvp.md) (PRD-1, shipped — local Cursor harness baseline)
- [docs/ARCHITECTURE_AND_IMPLEMENTATION_PLAN.md](../../docs/ARCHITECTURE_AND_IMPLEMENTATION_PLAN.md) (Phase 6; §8.3 cloud agents)
- [docs/OPEN_DECISIONS.md](../../docs/OPEN_DECISIONS.md) (D15 Cursor Cloud agent demo)

> Scope note: PRD-3 covers **architecture Phase 6 (stretch)** and is **independent of PRD-2/PRD-4**. It extends the existing Cursor harness from local to **Cursor-hosted cloud VMs**.

---

## ⚠️ Hard prerequisite (decide before sign-off)

Cursor Cloud agents clone a **GitHub repository** into a Cursor-hosted VM and require an **SCM connection** (D15). This **conflicts with the current stance** ("no remote push until everything is complete & tested"). PRD-3 cannot be exercised end-to-end until the repo is pushed to GitHub. So sign-off requires choosing one of:

- **(a) Push now** — the MVP + eval are green/tested; publish to a GitHub repo under the maintainer's org and connect SCM.
- **(b) Defer PRD-3** — keep the repo local; pick PRD-4 (GPU, fully local) first and return to PRD-3 when ready to publish.

This decision gates everything below.

---

## 1. Introduction / Overview

PRD-1 proved a **local** Cursor SDK agent driving Pipefy via MCP. PRD-3 demonstrates the **same agent in a Cursor-hosted cloud VM** (`CloudAgentOptions` + `repos`), running the canonical `inventory` scenario against Pipefy MCP **inside the VM** — showing the harness scales from laptop to managed runtime without changing the MCP contract.

---

## 2. Goals

1. Run the `inventory` scenario via a **Cursor Cloud agent** (`bc-…` id) against `pipefy-mcp-server` provisioned in the VM.
2. Demonstrate cloud lifecycle: `CloudAgentOptions(repos=[CloudRepository(...)])`, session `env_vars` for secrets (encrypted at rest), and `skip_reviewer_request` for quiet runs.
3. Provision `pipefy-mcp-server` inside the VM (the bridge depends on the binary on PATH).
4. Document the GitHub push + SCM-connection prerequisite and the security model for cloud secrets.

---

## 3. User Stories

- **As a maintainer**, I want to launch a cloud agent that runs `inventory` in a Cursor VM and returns the answer + `bc-` id, so that I can show the harness works without a local machine.
- **As a security reviewer**, I want Pipefy/NVIDIA secrets passed as session `env_vars` (encrypted, deleted with the agent), so that no secret is committed or persisted.

---

## 4. Functional Requirements

1. The repo MUST provide a cloud entrypoint (e.g. `demos/03_cursor_cloud_ops.py`) using `Agent.create(model="composer-2.5", cloud=CloudAgentOptions(repos=[CloudRepository(url=…, starting_ref=…)]))` plus inline `StdioMcpServerConfig(command="pipefy-mcp-server", env=…)`.
2. Secrets MUST be passed via `CloudAgentOptions.env_vars` (Pipefy service account, `NVIDIA_API_KEY` if needed); names MUST NOT start with `CURSOR_`; nothing committed.
3. The VM MUST have `pipefy-mcp-server` available before the agent runs (setup step — confirm mechanism: repo setup script / environment config / agent bootstrap step).
4. The entrypoint MUST log the `bc-` `agent_id` and the run result, and support `skip_reviewer_request`.
5. The entrypoint MUST reuse the **same** `inventory` prompt and remain read-only.
6. CI MUST remain lint-only; cloud runs are operator-invoked.

---

## 5. Non-Goals (Out of Scope)

1. Auto-PR / code-writing cloud workflows (beyond a read-only inventory demo).
2. Multi-repo or self-hosted pools.
3. Write/mutation Pipefy scenarios.
4. Replacing the local harness — cloud is an additional entrypoint.
5. NAT-in-cloud (this PRD is Cursor-cloud only).

---

## 6. Technical Considerations

- **Cursor SDK (verified):** `CloudAgentOptions(repos=[CloudRepository(url, starting_ref)], env_vars=…, skip_reviewer_request=…)`; cloud agents get `bc-` ids; stdio MCP `env` is injected into the VM (treat as runtime secret); `env_vars` encrypted at rest, deleted with the agent, cannot start with `CURSOR_`.
- **VM provisioning of `pipefy-mcp-server`:** the bridge needs the binary on PATH in the VM. Confirm the supported mechanism (repo-committed setup, environment snapshot, or an agent bootstrap step) — this is the main implementation unknown.
- **SCM:** requires the repo on GitHub + connected provider (`Cursor.repositories.list()` to confirm availability).
- **Security:** sandbox Pipefy org + minimum scope unchanged; cloud adds the VM trust boundary (secrets in `env_vars`, not in repo).

---

## 7. Success Metrics

1. A cloud agent run completes `inventory` in a Cursor-hosted VM and returns an answer consistent with the CLI baseline; `bc-` id logged.
2. No secret is committed; secrets flow only through `env_vars`.
3. CI stays lint-only and green.

---

## 8. Open Questions

1. **Push decision (the hard prerequisite above)** — push now vs defer.
2. **Target repo/branch** for `CloudRepository(url, starting_ref)`.
3. **VM provisioning** of `pipefy-mcp-server` — exact supported mechanism.
4. **Secret delivery** — session `env_vars` vs MCP servers configured on cursor.com/agents.
5. **Public vs private repo** for the demo (affects what can be shown).

---

## 9. Dependencies & Sequencing

- **Hard dependency:** repo pushed to GitHub + SCM connected (D15).
- **Independent of:** PRD-2 (eval) and PRD-4 (GPU). If the push decision is "defer", PRD-4 (fully local) is the better next move.
