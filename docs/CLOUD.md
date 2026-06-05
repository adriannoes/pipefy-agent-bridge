# Cursor Cloud — operator guide

Run the Pipefy **`inventory`** scenario (and other shared prompts) in a **Cursor-hosted VM** instead of on your laptop. The cloud path reuses the same prompts as `make demo-cursor`, but provisions a remote VM, clones this repo, and runs the Cursor SDK there.

> **Security:** Do **not** paste organization IDs, API keys, tokens, or service-account secrets into issues, PRs, chat logs, or screenshots. Keep secrets in **local `.env`** only; the cloud demo forwards them via encrypted session `env_vars` (see [Secret delivery](#secret-delivery) below).

---

## Prerequisites

| Requirement | Why |
|-------------|-----|
| **GitHub repo pushed** | The cloud VM clones your repo over HTTPS; unpushed commits are not visible. |
| **SCM connected in Cursor** | Connect GitHub at [cursor.com/agents](https://cursor.com/agents) so cloud agents can clone private repos you authorize. |
| **Local `uv` + Python 3.11+** | The operator machine runs `make demo-cloud` (same as the local Cursor demo). |
| **`make install-cursor-demo`** | Installs `cursor-sdk` and `python-dotenv` (also run automatically by `demo-cloud`). |
| **Bootstrap on the target ref** | `.cursor/environment.json` and `scripts/cloud_bootstrap.sh` must exist on the branch/tag set by `CLOUD_STARTING_REF` (default `main`) so the VM installs `pipefy-mcp-server` on boot. |

This workflow is **operator-invoked** (not CI). You need a valid **`CURSOR_API_KEY`** on your machine and Pipefy sandbox credentials in `.env`.

---

## Local environment (`.env`)

From the repository root:

```bash
cp .env.example .env
```

Edit `.env` with your own values (never commit `.env`). See [.env.example](../.env.example) for placeholders.

### Variables used by `make demo-cloud`

| Variable | Required | Where to get it | Notes |
|----------|----------|-----------------|-------|
| `CURSOR_API_KEY` | yes | [Cursor Dashboard → API Keys](https://cursor.com/dashboard/api) | Used **only** on the operator machine (`Agent.create(api_key=…)`). **Not** sent in `env_vars` (keys prefixed with `CURSOR_` are rejected by the SDK). |
| `PIPEFY_SERVICE_ACCOUNT_CLIENT_ID` | yes | Pipefy Admin → Service Accounts | Forwarded to the VM via `env_vars` and MCP stdio `env`. |
| `PIPEFY_SERVICE_ACCOUNT_CLIENT_SECRET` | yes | Same | Same forwarding as client ID. |
| `DEMO_ORG_ID` | yes for `inventory` | Your Pipefy organization ID | Org scope for the read-only inventory prompt; use a **sandbox** org. |
| `DEMO_PIPE_ID` | for `stale_cards` / `summary` | Numeric pipe ID | Not required for default `inventory`. |
| `DEMO_PHASE_NAME` | for `stale_cards` | Phase name in Pipefy UI | Not required for `inventory`. |
| `NVIDIA_API_KEY` | optional | [build.nvidia.com](https://build.nvidia.com/) | Forwarded if set; reserved for future cloud/NAT use. |
| `CLOUD_REPO_URL` | yes | Your fork or org mirror on GitHub | HTTPS Git URL cloned into the VM (see below). No maintainer default — set in `.env`. |
| `CLOUD_STARTING_REF` | optional | `main` | Branch or tag checked out in the VM (see below). |

**Preflight (recommended):**

```bash
make doctor
```

`make doctor` checks binaries and required env vars for the local tour; it warns if optional keys are missing but does not run a cloud agent.

---

## Repository URL and starting ref

The cloud entrypoint (`demos/03_cursor_cloud_ops.py`) passes these to `CloudAgentOptions.repos`:

| Variable | Default when unset | Purpose |
|----------|-------------------|---------|
| `CLOUD_REPO_URL` | *(none — required)* | HTTPS Git URL the VM clones (your fork or org mirror). Set in `.env`; `make demo-cloud` fails fast if missing. |
| `CLOUD_STARTING_REF` | `main` | Branch or tag checked out before the agent runs. Must contain `.cursor/environment.json` and `scripts/cloud_bootstrap.sh` for automatic MCP install. |

Set both in `.env` (see [.env.example](../.env.example)). Push provisioning artifacts to the ref you use before running demos or probes.

**Important:** Push provisioning artifacts to the ref you probe or demo against; otherwise the VM may not run `scripts/cloud_bootstrap.sh` on boot.

---

## Run the cloud demo (end-to-end)

1. Complete [Prerequisites](#prerequisites) and [Local environment](#local-environment-env).
2. Ensure the target branch is pushed to GitHub.
3. Run the same command as documented in the `Makefile`:

```bash
make demo-cloud SCENARIO=inventory
```

This target:

- Requires `.env` in the repo root (same as `demo-cursor`).
- Loads `.env` with `set -a && . ./.env && set +a`.
- Runs `PYTHONPATH=. uv run python demos/03_cursor_cloud_ops.py --scenario $(SCENARIO)` (`SCENARIO` defaults to `inventory`). `PYTHONPATH=.` is required so `demos.*` imports resolve when the script is run as a file path.

**Other scenarios** (same `SCENARIO=` as local Cursor):

```bash
make demo-cloud SCENARIO=stale_cards
make demo-cloud SCENARIO=summary
```

### What to expect

| Stream | Content |
|--------|---------|
| **stderr** | `agent_id=bc-…` (cloud agent id), `run_id=…`, optional `[tool] …` lines during MCP calls |
| **stdout** | Final natural-language answer (inventory pipe list, etc.) |

Record the **`bc-` agent id** from stderr for operator notes or support (do not paste secrets alongside it).

**Exit codes** (same contract as `demos/01_cursor_pipefy_ops.py`):

| Code | Meaning |
|------|---------|
| `0` | Run completed successfully |
| `1` | Startup / config failure (`CursorAgentError` or missing env) |
| `2` | Run finished with `status == "error"` |

For the local three-act tour, see [TRY_IT_YOURSELF.md](TRY_IT_YOURSELF.md). Cloud is an optional path after Steps 0–2.

---

## VM provisioning

### Decision (2026-06-04)

**Mechanism:** Repo-committed **`.cursor/environment.json`** with an **`install`** hook that runs **`scripts/cloud_bootstrap.sh`** on every cloud VM boot.

| Option considered | Verdict |
|-------------------|---------|
| `.cursor/environment.json` + `install` script | **Chosen** — official Cursor path; idempotent; cached between runs |
| Agent-driven first-step install | Fallback only (probe / pre-push); not relied on in production |
| Custom Dockerfile | Deferred — `uv tool install` is sufficient for the core tour |
| Dashboard snapshot only | Optional later — can reference a snapshot ID in `environment.json` after first green run |

### Why this path

- Cursor runs the `install` command **before the agent starts**, from the **project root** ([Cloud Environment Setup](https://cursor.com/docs/cloud-agent/setup)).
- The script mirrors **`make install-pipefy-tools`**: `uv tool install` of `pipefy-mcp-server` from **pipefy/ai-toolkit** at the pin in the `Makefile` (`PIPEFY_TOOLKIT_REF`, default `v0.2.0-beta.2`).
- Installs land in **`$HOME/.local/bin`**; the bootstrap script ensures that directory is on `PATH`.
- If `uv` is missing on the base image, the bootstrap installs it via Astral’s install script (idempotent).

### Artifacts

| File | Role |
|------|------|
| `.cursor/environment.json` | Declares `install: bash scripts/cloud_bootstrap.sh` |
| `scripts/cloud_bootstrap.sh` | Idempotent `uv` + `pipefy-mcp-server` install |
| `scripts/cloud_probe_vm.py` | Diagnostic: cloud agent verifies `--help` resolves |

### Validated probe (2026-06-04)

Probe run logged `agent_id=bc-8fe5d06e-0171-45a0-8000-2ca7d8883805` and `MCP_HELP_FIRST_LINE=pipefy-mcp-server 0.2.0-beta.2`.

> **Note:** `scripts/cloud_probe_vm.py` requires `scripts/cloud_bootstrap.sh` on the checked-out ref (no inline bootstrap fallback). Push that script to the branch set by `CLOUD_STARTING_REF` before running the probe.

---

## Secret delivery

### Decision (2026-06-04)

**Mechanism:** Pass session secrets via **`CloudAgentOptions.env_vars`** at agent creation (`demos/_cloud_config.build_env_vars`). The cloud demo **also** passes Pipefy keys in **`StdioMcpServerConfig.env`** for the MCP child process — same values, two injection points.

| Option considered | Verdict |
|-------------------|---------|
| `CloudAgentOptions.env_vars` only | **Primary** — session-scoped, encrypted at rest, deleted with the agent |
| MCP stdio `env` only | **Insufficient alone** — MCP subprocess only; agent shell/tools would not see keys |
| Both `env_vars` + MCP stdio `env` | **Shipped in `03_cursor_cloud_ops.py`** — VM-wide + MCP contract |
| Dashboard MCP servers (cursor.com/agents) | **Not used** — operator `.env` + SDK wiring keeps secrets out of the repo |
| Committed `.env` in the repo | **Forbidden** — `.env` stays local; only `.env.example` is committed |

### SDK constraints

- **`env_vars` keys MUST NOT start with `CURSOR_`** — pass `CURSOR_API_KEY` via `Agent.create(api_key=…)` only.
- **Values are encrypted at rest** per Cursor cloud-agent docs; scoped to the cloud agent session.
- **Logging:** entrypoint and probes log key **names** and counts, never values.

### Keys forwarded to the VM (`build_env_vars`)

| Key | Typical use |
|-----|-------------|
| `PIPEFY_SERVICE_ACCOUNT_CLIENT_ID` | Pipefy MCP auth |
| `PIPEFY_SERVICE_ACCOUNT_CLIENT_SECRET` | Pipefy MCP auth |
| `DEMO_ORG_ID` | Org scope (`inventory`) |
| `DEMO_PIPE_ID` | Pipe-scoped scenarios |
| `DEMO_PHASE_NAME` | `stale_cards` |
| `NVIDIA_API_KEY` | Optional |

MCP stdio `env` includes the Pipefy service-account pair, `DEMO_ORG_ID`, and `DEMO_PIPE_ID` when set (`demos/03_cursor_cloud_ops.py`).

### `env_vars` vs MCP stdio `env`

| Aspect | `CloudAgentOptions.env_vars` | `StdioMcpServerConfig.env` |
|--------|------------------------------|----------------------------|
| Scope | VM session / agent process environment | MCP server subprocess only |
| Encrypted at rest | yes (Cursor session secrets) | runtime secret in VM |
| Dashboard alternative | set from SDK | cursor.com/agents MCP config (avoided here) |
| This repo | **Primary** for all listed keys | **Duplicate Pipefy keys** for `pipefy-mcp-server` |

### Validated probe (2026-06-04)

Secrets probe logged `agent_id=bc-562d828d-80a6-46f2-9ddc-a2e0437282c5`; stdout reported `*_SET=true` for passed keys without echoing values.

| File | Role |
|------|------|
| `scripts/cloud_probe_secrets.py` | Diagnostic: verify `env_vars` reach the VM (no value echo) |

---

## Diagnostic probes (optional)

Use these only when changing provisioning or secret wiring—not required for the normal `make demo-cloud` path.

**VM provisioning (`pipefy-mcp-server` on PATH):**

```bash
set -a && . ./.env && set +a
PYTHONPATH=. uv run python scripts/cloud_probe_vm.py
```

Expect stderr: `agent_id=bc-…`, `run_id=…`; stdout contains `PROVISION_OK=true`.

**Secret delivery (`env_vars` in VM, no value leak):**

```bash
set -a && . ./.env && set +a
PYTHONPATH=. uv run python scripts/cloud_probe_secrets.py
```

Expect stderr: `passing env_vars keys (N): …`, `agent_id=bc-…`; stdout lines like `PIPEFY_SERVICE_ACCOUNT_CLIENT_ID_SET=true` and `SECRETS_PROBE_OK=true`.

---

## Related documentation

- [TRY_IT_YOURSELF.md](TRY_IT_YOURSELF.md) — local Steps 0–4 (primary path); optional cloud pointer
- [Makefile](../Makefile) — `demo-cloud` target and `make help` defaults for `CLOUD_*`
- `demos/03_cursor_cloud_ops.py` — cloud harness implementation
- `demos/_cloud_config.py` — offline-tested `build_env_vars` / `build_cloud_options`
