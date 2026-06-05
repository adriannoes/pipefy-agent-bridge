"""Tests for eval/golden_expect.py."""

from __future__ import annotations

from pathlib import Path

import pytest

from eval.golden_errors import GoldenLoadError
from eval.golden_expect import validate_expect_against_baseline

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_INVENTORY = REPO_ROOT / "eval" / "fixtures" / "example" / "inventory.json"
EXAMPLE_STALE_CARDS = REPO_ROOT / "eval" / "fixtures" / "example" / "stale_cards.json"
EXAMPLE_SUMMARY = REPO_ROOT / "eval" / "fixtures" / "example" / "summary.json"


def test_validate_expect_against_example_inventory() -> None:
    validate_expect_against_baseline(
        {
            "min_pipes": 3,
            "pipe_name_substrings": ["Onboarding", "Helpdesk"],
        },
        EXAMPLE_INVENTORY,
        scenario="inventory",
    )


def test_validate_expect_min_pipes_too_high() -> None:
    with pytest.raises(GoldenLoadError, match=r"min_pipes=99 exceeds"):
        validate_expect_against_baseline({"min_pipes": 99}, EXAMPLE_INVENTORY, scenario="inventory")


def test_validate_expect_unknown_substring() -> None:
    with pytest.raises(GoldenLoadError, match=r"pipe_name_substrings.*not found"):
        validate_expect_against_baseline(
            {"pipe_name_substrings": ["Nonexistent Pipe XYZ"]},
            EXAMPLE_INVENTORY,
            scenario="inventory",
        )


def test_validate_expect_against_example_stale_cards() -> None:
    validate_expect_against_baseline(
        {"min_stale_cards": 1, "card_title_substrings": ["Old onboarding"]},
        EXAMPLE_STALE_CARDS,
        scenario="stale_cards",
    )


def test_validate_expect_against_example_summary() -> None:
    validate_expect_against_baseline(
        {"min_cards": 3, "card_title_substrings": ["Newest open"]},
        EXAMPLE_SUMMARY,
        scenario="summary",
    )
