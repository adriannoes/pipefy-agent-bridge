"""Integration tests for eval/ground_truth.sh (live Pipefy CLI)."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
GROUND_TRUTH_SCRIPT = REPO_ROOT / "eval" / "ground_truth.sh"
LIVE_INVENTORY_BASELINE = REPO_ROOT / "eval" / "fixtures" / "live" / "inventory.json"


@pytest.mark.integration
def test_ground_truth_inventory_captures_valid_json_baseline() -> None:
    """Run ground_truth.sh inventory when Pipefy credentials and CLI are available."""
    if not (REPO_ROOT / ".env").is_file():
        pytest.skip(".env missing — copy .env.example to .env for live capture")

    env = os.environ.copy()
    result = subprocess.run(
        ["sh", str(GROUND_TRUTH_SCRIPT), "inventory"],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert result.returncode == 0, (
        f"ground_truth.sh failed (exit {result.returncode}): "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    assert LIVE_INVENTORY_BASELINE.is_file(), "expected live inventory baseline file"
    payload = json.loads(LIVE_INVENTORY_BASELINE.read_text(encoding="utf-8"))
    assert isinstance(payload, (dict, list))
