"""Validate golden ``expect`` facts against a committed example baseline (PRD-2)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from eval.compare import extract_baseline_facts, load_baseline
from eval.golden_errors import GoldenLoadError


def validate_expect_against_baseline(
    expect: dict[str, Any],
    baseline_path: Path,
) -> None:
    """Ensure ``expect`` is consistent with facts from *baseline_path*.

    Uses ``extract_baseline_facts`` (D12). ``expect`` is checked against the
    committed **example** fixture, not the live org baseline.

    Args:
        expect: Golden facts (e.g. ``min_pipes``, ``pipe_name_substrings``).
        baseline_path: Path to committed ``eval/fixtures/example/*.json``.

    Raises:
        GoldenLoadError: When ``expect`` contradicts the example baseline.
    """
    baseline = load_baseline(baseline_path)
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

    substrings = expect.get("pipe_name_substrings")
    if substrings is not None:
        if not isinstance(substrings, list) or not all(
            isinstance(item, str) and item.strip() for item in substrings
        ):
            msg = (
                f"expect pipe_name_substrings must be a non-empty list of strings, "
                f"got {substrings!r} (baseline {baseline_path.name})"
            )
            raise GoldenLoadError(msg)
        baseline_names_casefold = {name.casefold() for name in facts.pipe_names}
        for fragment in substrings:
            fragment_cf = fragment.strip().casefold()
            if not any(fragment_cf in name for name in baseline_names_casefold):
                msg = (
                    f"expect pipe_name_substring {fragment!r} not found in example baseline "
                    f"pipe names {list(facts.pipe_names)!r} ({baseline_path!s})"
                )
                raise GoldenLoadError(msg)
