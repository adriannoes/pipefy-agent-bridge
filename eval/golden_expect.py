"""Validate golden ``expect`` facts against a committed example baseline."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from eval.compare import (
    extract_baseline_facts,
    extract_stale_cards_baseline_facts,
    extract_summary_baseline_facts,
    load_baseline,
)
from eval.golden_errors import GoldenLoadError


def validate_expect_against_baseline(
    expect: dict[str, Any],
    baseline_path: Path,
    *,
    scenario: str,
) -> None:
    """Ensure ``expect`` is consistent with facts from *baseline_path*.

    Uses scenario-specific baseline extractors (D12). ``expect`` is checked against
    the committed **example** fixture, not the live org baseline.

    Args:
        expect: Golden facts (e.g. ``min_pipes``, ``min_stale_cards``).
        baseline_path: Path to committed ``eval/fixtures/example/*.json``.
        scenario: Golden scenario name (``inventory``, ``stale_cards``, ``summary``).

    Raises:
        GoldenLoadError: When ``expect`` contradicts the example baseline.
    """
    baseline = load_baseline(baseline_path)
    normalized = scenario.strip()

    if normalized == "inventory":
        _validate_inventory_expect(expect, baseline, baseline_path=baseline_path)
        return
    if normalized == "stale_cards":
        if not isinstance(baseline, dict):
            msg = (
                f"scenario {scenario!r}: stale_cards example baseline must be an object, "
                f"got {type(baseline).__name__!r} in {baseline_path!s}"
            )
            raise GoldenLoadError(msg)
        _validate_stale_cards_expect(expect, baseline, baseline_path=baseline_path)
        return
    if normalized == "summary":
        if not isinstance(baseline, dict):
            msg = (
                f"scenario {scenario!r}: summary example baseline must be an object, "
                f"got {type(baseline).__name__!r} in {baseline_path!s}"
            )
            raise GoldenLoadError(msg)
        _validate_summary_expect(expect, baseline, baseline_path=baseline_path)
        return

    msg = (
        f"scenario {scenario!r}: unsupported expect validation "
        f"(known: inventory, stale_cards, summary)"
    )
    raise GoldenLoadError(msg)


def _validate_inventory_expect(
    expect: dict[str, Any],
    baseline: dict[str, Any] | list[Any],
    *,
    baseline_path: Path,
) -> None:
    facts = extract_baseline_facts(baseline)

    min_pipes = expect.get("min_pipes")
    if min_pipes is not None:
        if not isinstance(min_pipes, int) or min_pipes < 0:
            msg = (
                f"scenario expect min_pipes must be a non-negative int, got {min_pipes!r} "
                f"(baseline {baseline_path.name})"
            )
            raise GoldenLoadError(msg)
        if min_pipes > facts.pipe_count:
            msg = (
                f"expect min_pipes={min_pipes} exceeds example baseline pipe_count="
                f"{facts.pipe_count} in {baseline_path!s}"
            )
            raise GoldenLoadError(msg)

    _validate_name_substrings(
        expect.get("pipe_name_substrings"),
        field_name="pipe_name_substrings",
        candidate_names=facts.pipe_names,
        baseline_path=baseline_path,
    )


def _validate_stale_cards_expect(
    expect: dict[str, Any],
    baseline: dict[str, Any],
    *,
    baseline_path: Path,
) -> None:
    facts = extract_stale_cards_baseline_facts(baseline)

    min_stale_cards = expect.get("min_stale_cards")
    if min_stale_cards is not None:
        if not isinstance(min_stale_cards, int) or min_stale_cards < 0:
            msg = (
                f"scenario expect min_stale_cards must be a non-negative int, "
                f"got {min_stale_cards!r} (baseline {baseline_path.name})"
            )
            raise GoldenLoadError(msg)
        if min_stale_cards > facts.stale_count:
            msg = (
                f"expect min_stale_cards={min_stale_cards} exceeds example baseline "
                f"stale_count={facts.stale_count} in {baseline_path!s}"
            )
            raise GoldenLoadError(msg)

    _validate_name_substrings(
        expect.get("card_title_substrings"),
        field_name="card_title_substrings",
        candidate_names=facts.card_titles,
        baseline_path=baseline_path,
    )


def _validate_summary_expect(
    expect: dict[str, Any],
    baseline: dict[str, Any],
    *,
    baseline_path: Path,
) -> None:
    facts = extract_summary_baseline_facts(baseline)

    min_cards = expect.get("min_cards")
    if min_cards is not None:
        if not isinstance(min_cards, int) or min_cards < 0:
            msg = (
                f"scenario expect min_cards must be a non-negative int, got {min_cards!r} "
                f"(baseline {baseline_path.name})"
            )
            raise GoldenLoadError(msg)
        if min_cards > facts.card_count:
            msg = (
                f"expect min_cards={min_cards} exceeds example baseline card_count="
                f"{facts.card_count} in {baseline_path!s}"
            )
            raise GoldenLoadError(msg)

    _validate_name_substrings(
        expect.get("card_title_substrings"),
        field_name="card_title_substrings",
        candidate_names=facts.card_titles,
        baseline_path=baseline_path,
    )


def _validate_name_substrings(
    substrings: Any,
    *,
    field_name: str,
    candidate_names: tuple[str, ...],
    baseline_path: Path,
) -> None:
    if substrings is None:
        return
    if not isinstance(substrings, list) or not all(
        isinstance(item, str) and item.strip() for item in substrings
    ):
        msg = (
            f"expect {field_name} must be a non-empty list of strings, "
            f"got {substrings!r} (baseline {baseline_path.name})"
        )
        raise GoldenLoadError(msg)
    baseline_names_casefold = {name.casefold() for name in candidate_names}
    for fragment in substrings:
        fragment_cf = fragment.strip().casefold()
        if not any(fragment_cf in name for name in baseline_names_casefold):
            msg = (
                f"expect {field_name} entry {fragment!r} not found in example baseline "
                f"names {list(candidate_names)!r} ({baseline_path!s})"
            )
            raise GoldenLoadError(msg)
