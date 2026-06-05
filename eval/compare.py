"""Fact-check agent inventory answers against Pipefy CLI JSON baselines (FR-21 / D12)."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_PIPE_COUNT_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(\d+)\s+pipes?\b", re.IGNORECASE),
    re.compile(r"\bpipes?\s*[:\-]?\s*(\d+)\b", re.IGNORECASE),
    re.compile(r"\btotal\s*(?:of\s*)?(\d+)\s+pipes?\b", re.IGNORECASE),
    re.compile(r"\b(\d+)\s+total\b", re.IGNORECASE),
)


@dataclass(frozen=True)
class InventoryFacts:
    """Pipe inventory facts extracted from a baseline or agent answer."""

    pipe_count: int
    pipe_names: tuple[str, ...]


def extract_baseline_facts(baseline: dict[str, Any] | list[Any]) -> InventoryFacts:
    """Extract pipe count and names from ``pipefy pipe list --json`` output.

    Args:
        baseline: Parsed CLI JSON (organizations wrapper or bare pipe array).

    Returns:
        Count and ordered pipe names from the baseline payload.

    Example:
        >>> payload = {"organizations": [{"pipes": [{"name": "Alpha"}], "pipesCount": 1}]}
        >>> extract_baseline_facts(payload).pipe_count
        1
    """
    if isinstance(baseline, list):
        names = _pipe_names_from_pipes(baseline)
        return InventoryFacts(pipe_count=len(names), pipe_names=names)

    organizations = baseline.get("organizations")
    if not isinstance(organizations, list):
        msg = f"expected organizations list in baseline, got {type(organizations).__name__!r}"
        raise ValueError(msg)

    names: list[str] = []
    declared_count = 0
    for org in organizations:
        if not isinstance(org, dict):
            continue
        pipes = org.get("pipes")
        if isinstance(pipes, list):
            names.extend(_pipe_names_from_pipes(pipes))
        org_count = org.get("pipesCount")
        if isinstance(org_count, int) and org_count >= 0:
            declared_count += org_count

    listed_count = len(names)
    pipe_count = _resolve_baseline_pipe_count(
        baseline if isinstance(baseline, dict) else {},
        declared_count=declared_count,
        listed_count=listed_count,
    )
    return InventoryFacts(pipe_count=pipe_count, pipe_names=tuple(names))


def extract_answer_facts(answer: str, baseline_names: tuple[str, ...]) -> InventoryFacts:
    """Extract stated pipe count and matched pipe names from agent answer text.

    Pipe names are baseline names found as case-insensitive substrings in ``answer``.
    Count is parsed from common prose patterns (e.g. ``3 pipes``).

    Args:
        answer: Free-form agent stdout or transcript text.
        baseline_names: Pipe names from the CLI baseline used for substring matching.

    Returns:
        Parsed count (``0`` when no explicit count is found) and matched names.
    """
    normalized_answer = answer.casefold()
    matched_names = tuple(
        name for name in baseline_names if _pipe_name_mentioned(name, normalized_answer)
    )
    pipe_count = _extract_stated_pipe_count(answer, expected=len(baseline_names) or None)
    return InventoryFacts(pipe_count=pipe_count, pipe_names=matched_names)


def compare_inventory_facts(
    baseline: InventoryFacts,
    answer: InventoryFacts,
) -> bool:
    """Return True when answer count matches baseline and every pipe name is present.

    Matching uses case-insensitive substring search for pipe names (D12).
    """
    if _effective_pipe_count(baseline) != _effective_pipe_count(answer):
        return False
    if len(answer.pipe_names) != len(baseline.pipe_names):
        return False
    return set(answer.pipe_names) == set(baseline.pipe_names)


def evaluate_inventory_answer(baseline: dict[str, Any] | list[Any], answer: str) -> bool:
    """Evaluate an agent answer against a CLI inventory baseline."""
    baseline_facts = extract_baseline_facts(baseline)
    answer_facts = extract_answer_facts(answer, baseline_facts.pipe_names)
    return compare_inventory_facts(baseline_facts, answer_facts)


@dataclass(frozen=True)
class StaleCardsFacts:
    """Stale-card facts extracted from a baseline or agent answer."""

    stale_count: int
    card_titles: tuple[str, ...]
    card_ids: tuple[str, ...]


@dataclass(frozen=True)
class SummaryFacts:
    """Summary-card facts extracted from a baseline or agent answer."""

    card_count: int
    card_titles: tuple[str, ...]


_CARD_COUNT_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(\d+)\s+(?:stale\s+)?cards?\b", re.IGNORECASE),
    re.compile(r"\bcards?\s*:\s*(\d+)\b", re.IGNORECASE),
    re.compile(r"\bfound\s+(\d+)\s+cards?\b", re.IGNORECASE),
    re.compile(r"\b(\d+)\s+(?:newest\s+)?(?:open\s+)?cards?\b", re.IGNORECASE),
)


def extract_stale_cards_baseline_facts(baseline: dict[str, Any]) -> StaleCardsFacts:
    """Extract stale-card count and identifiers from a normalized baseline."""
    stale_cards = baseline.get("stale_cards")
    if not isinstance(stale_cards, list):
        msg = f"expected stale_cards list in baseline, got {type(stale_cards).__name__!r}"
        raise ValueError(msg)
    titles: list[str] = []
    ids: list[str] = []
    for row in stale_cards:
        if not isinstance(row, dict):
            continue
        title = row.get("title")
        card_id = row.get("id")
        if isinstance(title, str) and title.strip():
            titles.append(title.strip())
        if isinstance(card_id, str) and card_id.strip():
            ids.append(card_id.strip())
    declared = baseline.get("stale_count")
    stale_count = declared if isinstance(declared, int) and declared >= 0 else len(titles)
    return StaleCardsFacts(
        stale_count=stale_count,
        card_titles=tuple(titles),
        card_ids=tuple(ids),
    )


def extract_summary_baseline_facts(baseline: dict[str, Any]) -> SummaryFacts:
    """Extract summary-card count and titles from a normalized baseline."""
    cards = baseline.get("cards")
    if not isinstance(cards, list):
        msg = f"expected cards list in baseline, got {type(cards).__name__!r}"
        raise ValueError(msg)
    titles: list[str] = []
    for row in cards:
        if not isinstance(row, dict):
            continue
        title = row.get("title")
        if isinstance(title, str) and title.strip():
            titles.append(title.strip())
    declared = baseline.get("card_count")
    card_count = declared if isinstance(declared, int) and declared >= 0 else len(titles)
    return SummaryFacts(card_count=card_count, card_titles=tuple(titles))


def extract_stale_cards_answer_facts(
    answer: str,
    baseline_titles: tuple[str, ...],
    baseline_ids: tuple[str, ...],
) -> StaleCardsFacts:
    """Extract stale-card count and matched titles/ids from agent answer text."""
    normalized_answer = answer.casefold()
    matched_titles = tuple(
        title for title in baseline_titles if _pipe_name_mentioned(title, normalized_answer)
    )
    matched_ids = tuple(
        card_id for card_id in baseline_ids if card_id.casefold() in normalized_answer
    )
    stale_count = _extract_stated_card_count(answer, expected=len(baseline_titles) or None)
    if stale_count == 0 and matched_titles:
        stale_count = len(matched_titles)
    return StaleCardsFacts(
        stale_count=stale_count,
        card_titles=matched_titles,
        card_ids=matched_ids,
    )


def extract_summary_answer_facts(answer: str, baseline_titles: tuple[str, ...]) -> SummaryFacts:
    """Extract summary-card count and matched titles from agent answer text."""
    normalized_answer = answer.casefold()
    matched_titles = tuple(
        title for title in baseline_titles if _pipe_name_mentioned(title, normalized_answer)
    )
    card_count = _extract_stated_card_count(answer, expected=len(baseline_titles) or None)
    if card_count == 0 and matched_titles:
        card_count = len(matched_titles)
    return SummaryFacts(card_count=card_count, card_titles=matched_titles)


def compare_stale_cards_facts(
    baseline: StaleCardsFacts,
    answer: StaleCardsFacts,
) -> bool:
    """Return True when answer count matches baseline and every stale card is cited."""
    if baseline.stale_count == 0:
        return answer.stale_count == 0
    if _effective_card_count(baseline) != _effective_card_count(answer):
        return False
    if len(answer.card_titles) != len(baseline.card_titles):
        return False
    return set(answer.card_titles) == set(baseline.card_titles)


def compare_summary_facts(baseline: SummaryFacts, answer: SummaryFacts) -> bool:
    """Return True when answer count matches baseline and every card title is present."""
    if baseline.card_count == 0:
        return answer.card_count == 0
    if _effective_card_count(baseline) != _effective_card_count(answer):
        return False
    if len(answer.card_titles) != len(baseline.card_titles):
        return False
    return set(answer.card_titles) == set(baseline.card_titles)


def evaluate_stale_cards_answer(baseline: dict[str, Any], answer: str) -> bool:
    """Evaluate an agent answer against a stale_cards baseline."""
    baseline_facts = extract_stale_cards_baseline_facts(baseline)
    answer_facts = extract_stale_cards_answer_facts(
        answer,
        baseline_facts.card_titles,
        baseline_facts.card_ids,
    )
    return compare_stale_cards_facts(baseline_facts, answer_facts)


def evaluate_summary_answer(baseline: dict[str, Any], answer: str) -> bool:
    """Evaluate an agent answer against a summary baseline."""
    baseline_facts = extract_summary_baseline_facts(baseline)
    answer_facts = extract_summary_answer_facts(answer, baseline_facts.card_titles)
    return compare_summary_facts(baseline_facts, answer_facts)


def evaluate_answer(
    baseline: dict[str, Any] | list[Any],
    answer: str,
    *,
    scenario: str,
) -> bool:
    """Dispatch scenario-specific fact checking against a baseline payload."""
    normalized = scenario.strip()
    if normalized == "inventory":
        return evaluate_inventory_answer(baseline, answer)
    if normalized == "stale_cards":
        if not isinstance(baseline, dict):
            msg = f"stale_cards baseline must be an object, got {type(baseline).__name__!r}"
            raise ValueError(msg)
        return evaluate_stale_cards_answer(baseline, answer)
    if normalized == "summary":
        if not isinstance(baseline, dict):
            msg = f"summary baseline must be an object, got {type(baseline).__name__!r}"
            raise ValueError(msg)
        return evaluate_summary_answer(baseline, answer)
    msg = f"unsupported eval scenario for scoring: {scenario!r}"
    raise ValueError(msg)


def _effective_card_count(facts: StaleCardsFacts | SummaryFacts) -> int:
    """Count from prose when present; otherwise infer from matched card titles."""
    count = facts.stale_count if isinstance(facts, StaleCardsFacts) else facts.card_count
    if count > 0:
        return count
    return len(facts.card_titles)


def _extract_stated_card_count(answer: str, *, expected: int | None = None) -> int:
    """Parse card counts from prose; prefer ``expected`` when multiple values appear."""
    values: list[int] = []
    for pattern in _CARD_COUNT_PATTERNS:
        for match in pattern.finditer(answer):
            values.append(int(match.group(1)))
    if not values:
        return 0
    if expected is not None and expected in values:
        return expected
    return values[0]


def _resolve_baseline_pipe_count(
    baseline: dict[str, Any],
    *,
    declared_count: int,
    listed_count: int,
) -> int:
    """Use listed pipe count when the CLI payload is truncated (FR-21 / D12).

    ``pipefy pipe list --json`` may set ``pipesCount`` to the org total while
    ``pipes[]`` only contains the first page; ``search_limits.pipes_truncated``
    or per-org ``pipes_truncated`` signals that mismatch.
    """
    if listed_count == 0:
        return declared_count if declared_count > 0 else 0
    if _baseline_pipes_truncated(
        baseline,
        declared_count=declared_count,
        listed_count=listed_count,
    ):
        return listed_count
    if declared_count > 0:
        return declared_count
    return listed_count


def _baseline_pipes_truncated(
    baseline: dict[str, Any],
    *,
    declared_count: int,
    listed_count: int,
) -> bool:
    limits = baseline.get("search_limits")
    if isinstance(limits, dict) and limits.get("pipes_truncated") is True:
        return True
    organizations = baseline.get("organizations")
    if isinstance(organizations, list):
        for org in organizations:
            if isinstance(org, dict) and org.get("pipes_truncated") is True:
                return True
    return declared_count > listed_count


def _effective_pipe_count(facts: InventoryFacts) -> int:
    """Count from prose when present; otherwise infer from matched pipe names."""
    if facts.pipe_count > 0:
        return facts.pipe_count
    return len(facts.pipe_names)


def _pipe_name_mentioned(pipe_name: str, answer_casefold: str) -> bool:
    """Return True when ``pipe_name`` appears in agent text (D12 substring + token fallback)."""
    if pipe_name.casefold() in answer_casefold:
        return True
    tokens = [token for token in re.findall(r"[a-z0-9]+", pipe_name.casefold()) if len(token) > 3]
    if len(tokens) < 2:
        return False
    hits = sum(1 for token in tokens if token in answer_casefold)
    return hits >= min(2, len(tokens))


def _pipe_names_from_pipes(pipes: list[Any]) -> tuple[str, ...]:
    names: list[str] = []
    for pipe in pipes:
        if not isinstance(pipe, dict):
            continue
        name = pipe.get("name")
        if isinstance(name, str) and name.strip():
            names.append(name.strip())
    return tuple(names)


def _extract_stated_pipe_count(answer: str, *, expected: int | None = None) -> int:
    """Parse pipe counts from prose; prefer ``expected`` when multiple values appear."""
    values: list[int] = []
    for pattern in _PIPE_COUNT_PATTERNS:
        for match in pattern.finditer(answer):
            values.append(int(match.group(1)))
    if not values:
        return 0
    if expected is not None and expected in values:
        return expected
    return values[0]


def load_baseline(path: Path) -> dict[str, Any] | list[Any]:
    raw = path.read_text(encoding="utf-8")
    payload = json.loads(raw)
    if not isinstance(payload, (dict, list)):
        msg = f"baseline JSON root must be object or array, got {type(payload).__name__!r}"
        raise ValueError(msg)
    return payload


def main(argv: list[str] | None = None) -> int:
    """CLI entry: ``compare.py --baseline <json> --answer <txt> [--scenario NAME]``."""
    parser = argparse.ArgumentParser(
        description="Compare agent answer against Pipefy CLI JSON baseline.",
    )
    parser.add_argument("--baseline", required=True, type=Path, help="Path to CLI JSON baseline")
    parser.add_argument("--answer", required=True, type=Path, help="Path to agent answer text")
    parser.add_argument(
        "--scenario",
        default=None,
        help="Scenario name (inventory, stale_cards, summary); inferred from baseline when omitted",
    )
    args = parser.parse_args(argv)

    baseline = load_baseline(args.baseline)
    answer = args.answer.read_text(encoding="utf-8")
    scenario = args.scenario
    if scenario is None and isinstance(baseline, dict):
        raw_scenario = baseline.get("scenario")
        if isinstance(raw_scenario, str) and raw_scenario.strip():
            scenario = raw_scenario.strip()
    if scenario is None:
        scenario = "inventory"
    passed = evaluate_answer(baseline, answer, scenario=scenario)
    print("✓" if passed else "✗")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
