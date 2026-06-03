"""Tests for eval/golden_loader.py golden.yaml validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from eval.golden_errors import GoldenLoadError
from eval.golden_loader import GoldenCase, load_golden

REPO_ROOT = Path(__file__).resolve().parents[1]
GOLDEN_PATH = REPO_ROOT / "eval" / "golden.yaml"
EXAMPLE_INVENTORY_BASELINE = REPO_ROOT / "eval" / "fixtures" / "example" / "inventory.json"


def test_load_golden_inventory_case() -> None:
    cases = load_golden(GOLDEN_PATH)
    assert len(cases) >= 1

    inventory = next(case for case in cases if case.scenario == "inventory")
    assert isinstance(inventory, GoldenCase)
    assert inventory.example_baseline == EXAMPLE_INVENTORY_BASELINE.resolve()
    assert inventory.expect["min_pipes"] == 3
    assert inventory.expect["pipe_name_substrings"] == [
        "Onboarding Requests",
        "IT Helpdesk",
        "Procurement",
    ]


def test_missing_example_baseline_raises(tmp_path: Path) -> None:
    golden_file = tmp_path / "golden.yaml"
    golden_file.write_text(
        "\n".join(
            [
                "- scenario: inventory",
                "  example_baseline: eval/fixtures/example/does_not_exist.json",
                "  expect:",
                "    min_pipes: 1",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(GoldenLoadError, match=r"example baseline file not found") as exc_info:
        load_golden(golden_file)

    message = str(exc_info.value)
    assert "inventory" in message
    assert "does_not_exist.json" in message


def test_empty_expect_raises(tmp_path: Path) -> None:
    golden_file = tmp_path / "golden.yaml"
    example_rel = EXAMPLE_INVENTORY_BASELINE.relative_to(REPO_ROOT).as_posix()
    golden_file.write_text(
        "\n".join(
            [
                "- scenario: inventory",
                f"  example_baseline: {example_rel}",
                "  expect: {}",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(GoldenLoadError, match=r"at least one fact key") as exc_info:
        load_golden(golden_file)

    assert "inventory" in str(exc_info.value)


def test_expect_min_pipes_exceeds_baseline_raises(tmp_path: Path) -> None:
    golden_file = tmp_path / "golden.yaml"
    example_rel = EXAMPLE_INVENTORY_BASELINE.relative_to(REPO_ROOT).as_posix()
    golden_file.write_text(
        "\n".join(
            [
                "- scenario: inventory",
                f"  example_baseline: {example_rel}",
                "  expect:",
                "    min_pipes: 99",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(GoldenLoadError, match=r"min_pipes=99 exceeds") as exc_info:
        load_golden(golden_file)

    assert "inventory" in str(exc_info.value)


def test_legacy_baseline_alias_loads_with_warning(tmp_path: Path) -> None:
    golden_file = tmp_path / "golden.yaml"
    golden_file.write_text(
        "\n".join(
            [
                "- scenario: inventory",
                f"  baseline: {EXAMPLE_INVENTORY_BASELINE.relative_to(REPO_ROOT).as_posix()}",
                "  expect:",
                "    min_pipes: 3",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.warns(DeprecationWarning, match=r"baseline.*deprecated"):
        cases = load_golden(golden_file)

    assert cases[0].example_baseline == EXAMPLE_INVENTORY_BASELINE.resolve()
