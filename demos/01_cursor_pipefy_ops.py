#!/usr/bin/env python3
"""Cursor SDK harness: send a fixed scenario prompt to a local agent with Pipefy MCP.

Example:
    make demo-cursor SCENARIO=inventory
    PYTHONPATH=. uv run python demos/01_cursor_pipefy_ops.py --scenario inventory

Exit codes: 0 success, 1 ``CursorAgentError`` (startup/config), 2 run finished with error status.
"""

from __future__ import annotations

import os
import sys

from cursor_sdk import Agent, AgentOptions, LocalAgentOptions, StdioMcpServerConfig

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
    """Entry point: load env, validate, run the selected scenario."""
    args = parse_scenario_args(argv)
    load_repo_env()

    scenario_env = SCENARIO_REQUIRED_ENV.get(args.scenario, ())
    require_env_vars(REQUIRED_ENV_KEYS + scenario_env)

    prompt = load_scenario_prompt(args.scenario)

    with Agent.create(
        AgentOptions(
            model=CURSOR_MODEL,
            local=LocalAgentOptions(cwd=os.getcwd()),
            mcp_servers={
                MCP_SERVER_NAME: StdioMcpServerConfig(
                    command=MCP_COMMAND,
                    env=pipefy_mcp_stdio_env(),
                ),
            },
        ),
    ) as agent:
        return run_agent_session(agent, prompt)


if __name__ == "__main__":
    sys.exit(main())
