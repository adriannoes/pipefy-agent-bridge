"""Shared helpers for Cursor cloud diagnostic probes."""

from __future__ import annotations

import os
import sys

from cursor_sdk import Agent, AgentOptions, CursorAgentError

from demos._cloud_config import (
    build_cloud_options,
    resolve_cloud_repo_url,
    resolve_cloud_starting_ref,
)
from demos._cursor_harness import CURSOR_MODEL, require_env_var


def run_cloud_probe_agent(
    prompt: str,
    *,
    env_vars: dict[str, str] | None = None,
) -> tuple[int, str | None]:
    """Create a cloud agent, run *prompt*, print ids and answer.

    Returns:
        ``(exit_code, answer_text)`` — exit codes 0/1/2; answer is ``None`` on startup failure.
    """
    api_key = require_env_var("CURSOR_API_KEY")
    session_env = env_vars if env_vars is not None else {}

    try:
        cloud = build_cloud_options(
            repo_url=resolve_cloud_repo_url(os.environ),
            starting_ref=resolve_cloud_starting_ref(os.environ),
            env_vars=session_env,
            skip_reviewer_request=True,
            auto_create_pr=False,
        )
    except ValueError as exc:
        print(f"startup failed: {exc}", file=sys.stderr)
        return 1, None

    try:
        with Agent.create(
            AgentOptions(model=CURSOR_MODEL, cloud=cloud),
            api_key=api_key,
        ) as agent:
            run = agent.send(prompt)
            print(f"agent_id={agent.agent_id}", file=sys.stderr)
            print(f"run_id={run.id}", file=sys.stderr)
            result = run.wait()
    except CursorAgentError as exc:
        print(f"startup failed: {exc}", file=sys.stderr)
        return 1, None

    if result.status == "error":
        print(f"run failed: run_id={result.id} status={result.status}", file=sys.stderr)
        return 2, None

    answer = run.text()
    if answer:
        print(answer)
    return 0, answer
