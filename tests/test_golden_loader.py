"""Tests for eval/golden_loader.py golden.yaml validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from eval.golden_loader import GoldenCase, GoldenLoadError, load_golden

REPO_ROOT = Path(__file__).resolve().parents[1]
GOLDEN_PATH = REPO_ROOT / "eval" / "golden.yaml"
EXAMPLE_INVENTORY_BASELINE = REPO_ROOT / "eval" / "fixtures" / "example" / "inventory.json"


def test_load_golden_inventory_case() -> None:
    cases = load_golden(GOLDEN_PATH)
    assert len(cases) >= 1

    inventory = next(case for case in cases if case.scenario == "inventory")
    assert isinstance(inventory, GoldenCase)
    assert inventory.baseline == EXAMPLE_INVENTORY_BASELINE.resolve()
    assert inventory.expect["min_pipes"] == 3
    assert inventory.expect["pipe_name_substrings"] == [
        "Onboarding Requests",
        "IT Helpdesk",
        "Procurement",
    ]


def test_missing_baseline_raises(tmp_path: Path) -> None:
    golden_file = tmp_path / "golden.yaml"
    golden_file.write_text(
        "\n".join(
            [
                "- scenario: inventory",
                "  baseline: eval/fixtures/example/does_not_exist.json",
                "  expect:",
                "    min_pipes: 1",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(GoldenLoadError, match=r"baseline file not found") as exc_info:
        load_golden(golden_file)

    message = str(exc_info.value)
    assert "inventory" in message
    assert "does_not_exist.json" in message


def test_empty_expect_raises(tmp_path: Path) -> None:
    golden_file = tmp_path / "golden.yaml"
    golden_file.write_text(
        "\n".join(
            [
                "- scenario: inventory",
                f"  baseline: {EXAMPLE_INVENTORY_BASELINE.relative_to(REPO_ROOT).as_posix()}",
                "  expect: {}",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(GoldenLoadError, match=r"at least one fact key") as exc_info:
        load_golden(golden_file)

    assert "inventory" in str(exc_info.value)
