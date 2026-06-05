"""Shared Cursor SDK harness helpers for local and cloud Pipefy demos."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING

from cursor_sdk import CursorAgentError, Run
from cursor_sdk.types import SDKMessage, SDKToolUseMessage
from dotenv import load_dotenv

if TYPE_CHECKING:
    from cursor_sdk import Agent

REPO_ROOT = Path(__file__).resolve().parent.parent
PROMPTS_DIR = REPO_ROOT / "demos" / "prompts"
DEFAULT_SCENARIO = "inventory"
CURSOR_MODEL = "composer-2.5"
MCP_SERVER_NAME = "pipefy"
MCP_COMMAND = "pipefy-mcp-server"

PIPEFY_MCP_ENV_KEYS: tuple[str, ...] = (
    "PIPEFY_SERVICE_ACCOUNT_CLIENT_ID",
    "PIPEFY_SERVICE_ACCOUNT_CLIENT_SECRET",
    "DEMO_ORG_ID",
    "DEMO_PIPE_ID",
    "DEMO_PHASE_NAME",
)

CLOUD_SESSION_ENV_KEYS: tuple[str, ...] = PIPEFY_MCP_ENV_KEYS + ("NVIDIA_API_KEY",)

REQUIRED_ENV_KEYS: tuple[str, ...] = (
    "CURSOR_API_KEY",
    "PIPEFY_SERVICE_ACCOUNT_CLIENT_ID",
    "PIPEFY_SERVICE_ACCOUNT_CLIENT_SECRET",
)

SCENARIO_REQUIRED_ENV: dict[str, tuple[str, ...]] = {
    "inventory": ("DEMO_ORG_ID",),
}


def parse_scenario_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI flags for Cursor Pipefy demo harnesses."""
    parser = argparse.ArgumentParser(
        description="Run a fixed Pipefy scenario through the Cursor SDK and Pipefy MCP (stdio).",
    )
    parser.add_argument(
        "--scenario",
        default=DEFAULT_SCENARIO,
        help=f"Prompt file stem under demos/prompts/ (default: {DEFAULT_SCENARIO})",
    )
    return parser.parse_args(argv)


def load_repo_env() -> None:
    """Load ``.env`` from the repository root when present."""
    env_path = REPO_ROOT / ".env"
    if env_path.is_file():
        load_dotenv(env_path, override=False)


def require_env_vars(names: tuple[str, ...]) -> None:
    """Exit with code 1 when any named environment variable is unset or empty."""
    missing = [name for name in names if not os.environ.get(name, "").strip()]
    if not missing:
        return
    print(
        f"error: missing required environment variable(s): {', '.join(missing)}",
        file=sys.stderr,
    )
    print("hint: copy .env.example to .env and run make doctor", file=sys.stderr)
    sys.exit(1)


def require_env_var(name: str) -> str:
    """Return a non-empty environment variable or exit with code 1."""
    require_env_vars((name,))
    return os.environ[name].strip()


def load_scenario_prompt(scenario: str) -> str:
    """Read ``demos/prompts/<scenario>.txt`` and return stripped prompt text."""
    prompt_path = PROMPTS_DIR / f"{scenario}.txt"
    if not prompt_path.is_file():
        print(f"error: prompt file not found: {prompt_path}", file=sys.stderr)
        sys.exit(1)
    text = prompt_path.read_text(encoding="utf-8").strip()
    if not text:
        print(f"error: prompt file is empty: {prompt_path}", file=sys.stderr)
        sys.exit(1)
    return text


def pipefy_mcp_stdio_env(environ: Mapping[str, str] | None = None) -> dict[str, str]:
    """Build stdio ``env`` for ``pipefy-mcp-server`` from ``environ`` (default: process env)."""
    source = os.environ if environ is None else environ
    env: dict[str, str] = {}
    for key in PIPEFY_MCP_ENV_KEYS:
        value = source.get(key, "").strip()
        if value:
            env[key] = value
    return env


def stream_tool_call_lines(run: Run) -> None:
    """Print ``[tool]`` lines for each MCP tool_call message on stderr."""
    for message in run.messages():
        if _is_tool_call_message(message):
            print(
                f"[tool] {message.name} {message.status} ({message.call_id})",
                file=sys.stderr,
            )


def _is_tool_call_message(message: SDKMessage) -> bool:
    return isinstance(message, SDKToolUseMessage) or getattr(message, "type", None) == "tool_call"


def run_agent_session(agent: Agent, prompt: str) -> int:
    """Send *prompt*, stream tool lines, wait, print answer (exit 0/1/2)."""
    try:
        run = agent.send(prompt)
        print(f"agent_id={agent.agent_id}", file=sys.stderr)
        print(f"run_id={run.id}", file=sys.stderr)
        stream_tool_call_lines(run)
        result = run.wait()
    except CursorAgentError as exc:
        print(f"startup failed: {exc}", file=sys.stderr)
        return 1

    if result.status == "error":
        print(f"run failed: run_id={result.id} status={result.status}", file=sys.stderr)
        return 2

    answer = run.text()
    if answer:
        print(answer)
    return 0
