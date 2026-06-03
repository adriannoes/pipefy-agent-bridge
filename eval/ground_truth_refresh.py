"""Refresh live CLI baselines via ``eval/ground_truth.sh`` before scoring (PRD-2)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
LIVE_BASELINE_DIR = REPO_ROOT / "eval" / "fixtures" / "live"
_GROUND_TRUTH_SCRIPT = REPO_ROOT / "eval" / "ground_truth.sh"
_DEFAULT_TIMEOUT_S = 120.0


def scoring_baseline_path(scenario: str) -> Path:
    """Path to the live baseline JSON used for harness scoring."""
    if not scenario.strip():
        msg = f"scenario must be a non-empty string, got {scenario!r}"
        raise ValueError(msg)
    return LIVE_BASELINE_DIR / f"{scenario.strip()}.json"


def refresh_ground_truth(
    scenario: str,
    *,
    repo_root: Path = REPO_ROOT,
    timeout_s: float = _DEFAULT_TIMEOUT_S,
) -> Path:
    """Run ``ground_truth.sh`` for *scenario* and return the live baseline path.

    Args:
        scenario: Scenario name (e.g. ``inventory``).
        repo_root: Repository root (``ground_truth.sh`` cwd).
        timeout_s: Subprocess timeout in seconds.

    Returns:
        Resolved path to ``eval/fixtures/live/<scenario>.json``.

    Raises:
        ValueError: When *scenario* is empty.
        RuntimeError: When the script fails or the baseline file is missing.
    """
    if not scenario.strip():
        msg = f"scenario must be a non-empty string, got {scenario!r}"
        raise ValueError(msg)

    script = repo_root / "eval" / "ground_truth.sh"
    if not script.is_file():
        msg = f"ground_truth script not found: {script!s}"
        raise RuntimeError(msg)

    completed = subprocess.run(
        [str(script), scenario.strip()],
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=timeout_s,
        check=False,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip()
        msg = (
            f"ground_truth.sh {scenario!r} failed (exit {completed.returncode})"
            f"{': ' + detail if detail else ''}"
        )
        raise RuntimeError(msg)

    out_path = scoring_baseline_path(scenario)
    if not out_path.is_file():
        msg = (
            f"ground_truth.sh succeeded but baseline file missing: {out_path!s} "
            f"(expected after refresh for scenario {scenario!r})"
        )
        raise RuntimeError(msg)

    return out_path.resolve()


def main(argv: list[str] | None = None) -> int:
    """CLI: refresh one scenario baseline (operator helper)."""
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "scenario",
        nargs="?",
        default="inventory",
        help="Scenario name (default: inventory)",
    )
    args = parser.parse_args(argv)
    path = refresh_ground_truth(args.scenario)
    print(path, file=sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
