#!/usr/bin/env python3
"""Cloud probe: verify secrets reach the VM via ``env_vars``.

Example:
    set -a && . ./.env && set +a
    PYTHONPATH=. uv run python scripts/cloud_probe_secrets.py

Exit codes: 0 success, 1 CursorAgentError (startup/config), 2 run finished with error status.
"""

from __future__ import annotations

import os
import sys

from demos._cursor_harness import load_repo_env, require_env_var
from scripts._cloud_probe_common import run_cloud_probe_agent

DEFAULT_PROBE_MARKER = "pipefy-agent-bridge-secrets-probe"

REQUIRED_LOCAL_KEYS: tuple[str, ...] = (
    "CURSOR_API_KEY",
    "PIPEFY_SERVICE_ACCOUNT_CLIENT_ID",
    "PIPEFY_SERVICE_ACCOUNT_CLIENT_SECRET",
)

CLOUD_SECRET_KEYS: tuple[str, ...] = (
    "PIPEFY_SERVICE_ACCOUNT_CLIENT_ID",
    "PIPEFY_SERVICE_ACCOUNT_CLIENT_SECRET",
)

OPTIONAL_CLOUD_SECRET_KEYS: tuple[str, ...] = (
    "NVIDIA_API_KEY",
    "DEMO_ORG_ID",
)


def build_probe_env_vars() -> dict[str, str]:
    """Collect probe secrets from the local process environment for ``env_vars``."""
    marker = os.environ.get("CLOUD_PROBE_MARKER", "").strip() or DEFAULT_PROBE_MARKER
    env_vars: dict[str, str] = {"CLOUD_PROBE_MARKER": marker}

    for key in CLOUD_SECRET_KEYS:
        value = os.environ.get(key, "").strip()
        if value:
            env_vars[key] = value

    for key in OPTIONAL_CLOUD_SECRET_KEYS:
        value = os.environ.get(key, "").strip()
        if value:
            env_vars[key] = value

    return env_vars


def build_probe_prompt(expected_keys: tuple[str, ...]) -> str:
    """Return a prompt that checks presence of env vars without printing values."""
    key_lines = "\n".join(f"- {key}" for key in expected_keys)
    expected_lines = "\n".join(f"{key}_SET=true|false" for key in expected_keys)
    return f"""\
You are running a secret-delivery diagnostic inside a Cursor cloud VM.

The operator passed session secrets via CloudAgentOptions.env_vars (encrypted at rest).
Check whether each variable is **set and non-empty** in the VM process environment.

Variables to check (names only — never print values):
{key_lines}

For each variable, run a shell or Python check that outputs only SET=true or SET=false.
Example (do not echo the value):
  python3 -c "import os; v=os.environ.get('VARNAME','').strip(); \\
    print('VARNAME_SET=' + ('true' if v else 'false'))"

Reply with exactly these lines (one per variable, then a summary):
{expected_lines}
SECRETS_PROBE_OK=true

Rules:
- Do not print secret values, prefixes, suffixes, or lengths.
- Do not use MCP tools. Do not modify any files. Read-only verification only.
"""


def run_cloud_probe() -> int:
    """Launch a cloud agent that verifies ``env_vars`` secrets are visible in the VM."""
    env_vars = build_probe_env_vars()
    expected_keys = tuple(sorted(env_vars))

    print(
        f"passing env_vars keys ({len(env_vars)}): {', '.join(expected_keys)}",
        file=sys.stderr,
    )

    exit_code, answer = run_cloud_probe_agent(
        build_probe_prompt(expected_keys),
        env_vars=env_vars,
    )
    if exit_code != 0:
        return exit_code

    if not answer or "SECRETS_PROBE_OK=true" not in answer:
        print("error: probe answer missing SECRETS_PROBE_OK=true", file=sys.stderr)
        return 2

    for key in expected_keys:
        if f"{key}_SET=true" not in answer:
            print(f"error: probe answer missing {key}_SET=true", file=sys.stderr)
            return 2

    return 0


def main() -> int:
    load_repo_env()
    for key in REQUIRED_LOCAL_KEYS:
        require_env_var(key)
    require_env_var("CLOUD_REPO_URL")
    return run_cloud_probe()


if __name__ == "__main__":
    sys.exit(main())
