"""Tests for eval/golden_expect.py."""

from __future__ import annotations

from pathlib import Path

import pytest

from eval.golden_errors import GoldenLoadError
from eval.golden_expect import validate_expect_against_baseline

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_INVENTORY = REPO_ROOT / "eval" / "fixtures" / "example" / "inventory.json"


def test_validate_expect_against_example_inventory() -> None:
    validate_expect_against_baseline(
        {
            "min_pipes": 3,
            "pipe_name_substrings": ["Onboarding", "Helpdesk"],
        },
        EXAMPLE_INVENTORY,
    )


def test_validate_expect_min_pipes_too_high() -> None:
    with pytest.raises(GoldenLoadError, match=r"min_pipes=99 exceeds"):
        validate_expect_against_baseline({"min_pipes": 99}, EXAMPLE_INVENTORY)


def test_validate_expect_unknown_substring() -> None:
    with pytest.raises(GoldenLoadError, match=r"pipe_name_substring.*not found"):
        validate_expect_against_baseline(
            {"pipe_name_substrings": ["Nonexistent Pipe XYZ"]},
            EXAMPLE_INVENTORY,
        )
