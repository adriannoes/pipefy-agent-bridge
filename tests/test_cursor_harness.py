"""Offline unit tests for demos/_cursor_harness.py."""

from __future__ import annotations

from pathlib import Path

import pytest

from demos import _cursor_harness as harness


def test_pipefy_mcp_stdio_env_selects_only_pipefy_keys() -> None:
    environ = {
        "PIPEFY_SERVICE_ACCOUNT_CLIENT_ID": "cid",
        "PIPEFY_SERVICE_ACCOUNT_CLIENT_SECRET": "secret",
        "DEMO_ORG_ID": "1",
        "NVIDIA_API_KEY": "nv",
        "CURSOR_API_KEY": "cursor",
    }

    assert harness.pipefy_mcp_stdio_env(environ) == {
        "PIPEFY_SERVICE_ACCOUNT_CLIENT_ID": "cid",
        "PIPEFY_SERVICE_ACCOUNT_CLIENT_SECRET": "secret",
        "DEMO_ORG_ID": "1",
    }
    assert "NVIDIA_API_KEY" not in harness.pipefy_mcp_stdio_env(environ)


def test_load_scenario_prompt_reads_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "custom.txt").write_text("  hello scenario  \n", encoding="utf-8")
    monkeypatch.setattr(harness, "PROMPTS_DIR", prompts_dir)

    assert harness.load_scenario_prompt("custom") == "hello scenario"


def test_load_scenario_prompt_exits_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(harness, "PROMPTS_DIR", harness.REPO_ROOT / "nonexistent-prompts-dir")

    with pytest.raises(SystemExit) as exc_info:
        harness.load_scenario_prompt("missing")

    assert exc_info.value.code == 1
