"""Load and validate ``eval/golden.yaml`` golden evaluation cases (PRD-2 FR-1)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

_REQUIRED_CASE_KEYS = frozenset({"scenario", "baseline", "expect"})


@dataclass(frozen=True)
class GoldenCase:
    """One golden scenario: CLI baseline path and expected facts for scoring."""

    scenario: str
    baseline: Path
    expect: dict[str, Any]


class GoldenLoadError(ValueError):
    """Raised when ``golden.yaml`` fails structural or filesystem validation."""


def load_golden(path: Path | str) -> list[GoldenCase]:
    """Load golden cases from a YAML list file.

    Each entry must include ``scenario``, ``baseline`` (repo-root-relative path
    to a committed fixture), and ``expect`` (non-empty dict of fact keys).

    Args:
        path: Path to ``golden.yaml`` (or equivalent).

    Returns:
        Validated cases in file order.

    Raises:
        GoldenLoadError: On parse errors, missing keys, empty ``expect``, or a
            missing baseline file.

    Example:
        >>> cases = load_golden("eval/golden.yaml")
        >>> cases[0].scenario
        'inventory'
    """
    golden_path = Path(path).resolve()
    repo_root = _find_repo_root(golden_path)
    raw_entries = _load_yaml_list(golden_path)
    cases: list[GoldenCase] = []
    for index, entry in enumerate(raw_entries):
        cases.append(_parse_case(entry, index=index, repo_root=repo_root))
    return cases


def _find_repo_root(start: Path) -> Path:
    search_from = start.parent if start.is_file() else start
    for parent in (search_from, *search_from.parents):
        if (parent / "pyproject.toml").is_file():
            return parent

    module_anchor = Path(__file__).resolve().parents[1]
    if (module_anchor / "pyproject.toml").is_file():
        return module_anchor

    msg = f"could not locate repo root (pyproject.toml) from golden file {start!s}"
    raise GoldenLoadError(msg)


def _load_yaml_list(golden_path: Path) -> list[Any]:
    if not golden_path.is_file():
        msg = f"golden file not found: {golden_path!s} (expected a readable YAML file)"
        raise GoldenLoadError(msg)

    try:
        payload = yaml.safe_load(golden_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        msg = f"golden file {golden_path!s} is not valid YAML: {exc}"
        raise GoldenLoadError(msg) from exc

    if not isinstance(payload, list):
        msg = (
            f"golden file {golden_path!s} root must be a YAML list of scenarios, "
            f"got {type(payload).__name__!r}; expected "
            "[{{scenario: str, baseline: str, expect: dict}}, ...]"
        )
        raise GoldenLoadError(msg)

    return payload


def _parse_case(entry: Any, *, index: int, repo_root: Path) -> GoldenCase:
    location = f"entry[{index}]"

    if not isinstance(entry, dict):
        msg = (
            f"{location}: each scenario must be a mapping with keys "
            f"{sorted(_REQUIRED_CASE_KEYS)!r}, got {type(entry).__name__!r}"
        )
        raise GoldenLoadError(msg)

    scenario_label = _scenario_label(entry, location=location)
    missing = sorted(_REQUIRED_CASE_KEYS - entry.keys())
    if missing:
        msg = (
            f"scenario {scenario_label!r}: missing required field(s) {missing!r}; "
            f"expected mapping with keys {sorted(_REQUIRED_CASE_KEYS)!r}"
        )
        raise GoldenLoadError(msg)

    scenario = _require_non_empty_str(
        entry["scenario"],
        field="scenario",
        scenario_label=scenario_label,
    )
    baseline_raw = _require_non_empty_str(
        entry["baseline"],
        field="baseline",
        scenario_label=scenario,
    )
    expect = _parse_expect(entry["expect"], scenario_label=scenario)

    baseline_path = _resolve_baseline_path(baseline_raw, repo_root=repo_root)
    if not baseline_path.is_file():
        msg = (
            f"scenario {scenario!r}: baseline file not found: {baseline_path!s} "
            f"(from {baseline_raw!r} relative to repo root {repo_root!s})"
        )
        raise GoldenLoadError(msg)

    return GoldenCase(scenario=scenario, baseline=baseline_path, expect=expect)


def _scenario_label(entry: dict[str, Any], *, location: str) -> str:
    scenario = entry.get("scenario")
    if isinstance(scenario, str) and scenario.strip():
        return scenario.strip()
    return location


def _require_non_empty_str(value: Any, *, field: str, scenario_label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        msg = (
            f"scenario {scenario_label!r}: field {field!r} must be a non-empty string, "
            f"got {value!r}"
        )
        raise GoldenLoadError(msg)
    return value.strip()


def _parse_expect(value: Any, *, scenario_label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        msg = (
            f"scenario {scenario_label!r}: field 'expect' must be a mapping of fact keys, "
            f"got {type(value).__name__!r}; expected e.g. "
            "{{min_pipes: int, pipe_name_substrings: list[str]}}"
        )
        raise GoldenLoadError(msg)

    if not value:
        msg = (
            f"scenario {scenario_label!r}: field 'expect' must contain at least one fact key "
            f"(e.g. min_pipes, pipe_name_substrings), got empty dict {{}}"
        )
        raise GoldenLoadError(msg)

    return dict(value)


def _resolve_baseline_path(baseline_raw: str, *, repo_root: Path) -> Path:
    candidate = Path(baseline_raw)
    if candidate.is_absolute():
        return candidate.resolve()
    return (repo_root / candidate).resolve()
