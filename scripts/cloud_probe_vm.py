#!/usr/bin/env python3
"""Cloud probe: verify pipefy-mcp-server resolves in the VM.

Requires ``scripts/cloud_bootstrap.sh`` on the branch set by ``CLOUD_STARTING_REF``.

Example:
    set -a && . ./.env && set +a
    PYTHONPATH=. uv run python scripts/cloud_probe_vm.py

Exit codes: 0 success, 1 CursorAgentError (startup/config), 2 run finished with error status.
"""

from __future__ import annotations

import sys

from demos._cursor_harness import load_repo_env, require_env_var
from scripts._cloud_probe_common import run_cloud_probe_agent

PROBE_PROMPT = """\
You are running a cloud VM provisioning diagnostic inside a Cursor cloud VM.

1. Run `bash scripts/cloud_bootstrap.sh` (must exist on the checked-out ref).
2. Run `pipefy-mcp-server --help` and confirm exit code 0.
3. Reply with exactly two lines:
   PROVISION_OK=true
   MCP_HELP_FIRST_LINE=<first non-empty line of --help output>

Do not use MCP tools. Do not modify any files. Read-only verification only.
"""


def run_cloud_probe() -> int:
    """Launch a cloud agent that bootstraps pipefy-mcp-server and verifies --help."""
    exit_code, answer = run_cloud_probe_agent(PROBE_PROMPT)
    if exit_code != 0:
        return exit_code
    if answer and "PROVISION_OK=true" in answer:
        return 0
    print("error: probe answer missing PROVISION_OK=true", file=sys.stderr)
    return 2


def main() -> int:
    load_repo_env()
    require_env_var("CURSOR_API_KEY")
    require_env_var("CLOUD_REPO_URL")
    return run_cloud_probe()


if __name__ == "__main__":
    sys.exit(main())
