"""Offline tests for eval/ground_truth_refresh.py."""

from __future__ import annotations

from pathlib import Path

import pytest

from eval import ground_truth_refresh as gt


def test_scoring_baseline_path_inventory() -> None:
    path = gt.scoring_baseline_path("inventory")
    assert path == gt.LIVE_BASELINE_DIR / "inventory.json"


def test_scoring_baseline_path_rejects_empty_scenario() -> None:
    with pytest.raises(ValueError, match=r"non-empty string"):
        gt.scoring_baseline_path("  ")


def test_refresh_ground_truth_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = tmp_path / "repo"
    script = repo_root / "eval" / "ground_truth.sh"
    live_dir = repo_root / "eval" / "fixtures" / "live"
    script.parent.mkdir(parents=True)
    live_dir.mkdir(parents=True)
    script.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    script.chmod(0o755)
    baseline = live_dir / "inventory.json"
    baseline.write_text('{"organizations": []}\n', encoding="utf-8")

    def fake_run(cmd: list[str], **kwargs: object) -> object:
        assert cmd[-1] == "inventory"
        assert kwargs.get("cwd") == repo_root

        class _Result:
            returncode = 0
            stdout = ""
            stderr = ""

        return _Result()

    monkeypatch.setattr(gt.subprocess, "run", fake_run)
    monkeypatch.setattr(gt, "REPO_ROOT", repo_root)
    monkeypatch.setattr(gt, "LIVE_BASELINE_DIR", live_dir)

    out = gt.refresh_ground_truth("inventory", repo_root=repo_root)
    assert out == baseline.resolve()


def test_refresh_ground_truth_script_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    script = repo_root / "eval" / "ground_truth.sh"
    script.parent.mkdir(parents=True)
    script.write_text("#!/bin/sh\nexit 2\n", encoding="utf-8")
    script.chmod(0o755)

    def fake_run(cmd: list[str], **kwargs: object) -> object:
        class _Result:
            returncode = 2
            stdout = ""
            stderr = "pipefy failed"

        return _Result()

    monkeypatch.setattr(gt.subprocess, "run", fake_run)
    monkeypatch.setattr(gt, "REPO_ROOT", repo_root)

    with pytest.raises(RuntimeError, match=r"ground_truth.sh.*failed"):
        gt.refresh_ground_truth("inventory", repo_root=repo_root)
