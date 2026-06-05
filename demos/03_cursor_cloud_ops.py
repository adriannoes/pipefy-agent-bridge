#!/usr/bin/env python3
"""Cursor SDK cloud harness: send a fixed scenario prompt to a cloud VM with Pipefy MCP.

Example:
    make demo-cloud SCENARIO=inventory
    PYTHONPATH=. uv run python demos/03_cursor_cloud_ops.py --scenario inventory

Exit codes: 0 success, 1 ``CursorAgentError`` (startup/config), 2 run finished with error status.
"""

from __future__ import annotations

import os
import sys

from cursor_sdk import Agent, AgentOptions, StdioMcpServerConfig

from demos._cloud_config import (
    build_cloud_options,
    build_env_vars,
    resolve_cloud_repo_url,
    resolve_cloud_starting_ref,
)
from demos._cursor_harness import (
    CURSOR_MODEL,
    MCP_COMMAND,
    MCP_SERVER_NAME,
    REQUIRED_ENV_KEYS,
    SCENARIO_REQUIRED_ENV,
    load_repo_env,
    load_scenario_prompt,
    parse_scenario_args,
    pipefy_mcp_stdio_env,
    require_env_vars,
    run_agent_session,
)


def main(argv: list[str] | None = None) -> int:
    """Entry point: load env, validate, run the selected scenario in a cloud VM."""
    args = parse_scenario_args(argv)
    load_repo_env()

    scenario_env = SCENARIO_REQUIRED_ENV.get(args.scenario, ())
    require_env_vars(REQUIRED_ENV_KEYS + scenario_env)

    try:
        cloud = build_cloud_options(
            repo_url=resolve_cloud_repo_url(os.environ),
            starting_ref=resolve_cloud_starting_ref(os.environ),
            env_vars=build_env_vars(os.environ),
            skip_reviewer_request=True,
            auto_create_pr=False,
        )
    except ValueError as exc:
        print(f"startup failed: {exc}", file=sys.stderr)
        sys.exit(1)

    prompt = load_scenario_prompt(args.scenario)
    api_key = os.environ.get("CURSOR_API_KEY", "").strip()

    with Agent.create(
        AgentOptions(
            model=CURSOR_MODEL,
            cloud=cloud,
            mcp_servers={
                MCP_SERVER_NAME: StdioMcpServerConfig(
                    command=MCP_COMMAND,
                    env=pipefy_mcp_stdio_env(),
                ),
            },
        ),
        api_key=api_key,
    ) as agent:
        return run_agent_session(agent, prompt)


if __name__ == "__main__":
    sys.exit(main())
