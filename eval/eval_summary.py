"""Aggregate evaluation run results into reliability and latency summaries (PRD-2 FR-7)."""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from typing import Literal

HarnessName = Literal["cursor", "nat"]


@dataclass(frozen=True)
class RunResult:
    """One harness invocation (one attempt within a run episode)."""

    scenario: str
    harness: HarnessName
    run: int
    attempt: int
    passed: bool
    latency_s: float


@dataclass(frozen=True)
class HarnessSummary:
    """Aggregated metrics for one harness."""

    harness: HarnessName
    n_episodes: int
    first_attempt_pass_rate: float
    with_retries_pass_rate: float
    median_latency_s: float
    p90_latency_s: float


@dataclass(frozen=True)
class Summary:
    """Full evaluation summary across harnesses."""

    retries: int
    by_harness: tuple[HarnessSummary, ...]


def percentile(values: list[float], p: float) -> float:
    """Linear-interpolation percentile (p in 0–100); empty list returns 0.0."""
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    sorted_vals = sorted(values)
    rank = (len(sorted_vals) - 1) * (p / 100.0)
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return sorted_vals[int(rank)]
    weight = rank - lower
    return sorted_vals[lower] * (1.0 - weight) + sorted_vals[upper] * weight


@dataclass(frozen=True)
class _EpisodeOutcome:
    first_passed: bool
    with_retries_passed: bool
    latency_s: float


def summarize(results: list[RunResult], retries: int) -> Summary:
    """Aggregate per-harness pass rates and episode latency percentiles.

    Episodes are grouped by ``(scenario, harness, run)``. Episode latency is the
    sum of attempt latencies for that episode (all attempts recorded, including
    early stop after a pass).
    """
    if retries < 1:
        msg = f"retries must be >= 1, got {retries!r}"
        raise ValueError(msg)

    harnesses = _harnesses_in_results(results)
    summaries: list[HarnessSummary] = []
    for harness in harnesses:
        harness_rows = [row for row in results if row.harness == harness]
        episodes = _group_episodes(harness_rows, retries=retries)
        n_episodes = len(episodes)
        if n_episodes == 0:
            summaries.append(
                HarnessSummary(
                    harness=harness,
                    n_episodes=0,
                    first_attempt_pass_rate=0.0,
                    with_retries_pass_rate=0.0,
                    median_latency_s=0.0,
                    p90_latency_s=0.0,
                )
            )
            continue

        first_pass = sum(1 for ep in episodes if ep.first_passed)
        with_retries_pass = sum(1 for ep in episodes if ep.with_retries_passed)
        latencies = [ep.latency_s for ep in episodes]

        summaries.append(
            HarnessSummary(
                harness=harness,
                n_episodes=n_episodes,
                first_attempt_pass_rate=first_pass / n_episodes,
                with_retries_pass_rate=with_retries_pass / n_episodes,
                median_latency_s=percentile(latencies, 50.0),
                p90_latency_s=percentile(latencies, 90.0),
            )
        )

    return Summary(retries=retries, by_harness=tuple(summaries))


def _harnesses_in_results(results: list[RunResult]) -> tuple[HarnessName, ...]:
    order: list[HarnessName] = []
    for harness in ("cursor", "nat"):
        if any(row.harness == harness for row in results):
            order.append(harness)
    return tuple(order)


def _group_episodes(rows: list[RunResult], *, retries: int) -> list[_EpisodeOutcome]:
    by_episode: dict[tuple[str, int], list[RunResult]] = {}
    for row in rows:
        key = (row.scenario, row.run)
        by_episode.setdefault(key, []).append(row)

    outcomes: list[_EpisodeOutcome] = []
    for episode_rows in by_episode.values():
        attempts = {row.attempt: row for row in episode_rows}
        first = attempts.get(1)
        first_passed = first.passed if first is not None else False
        with_retries_passed = any(
            attempts.get(attempt) is not None and attempts[attempt].passed
            for attempt in range(1, retries + 1)
        )
        ordered = sorted(episode_rows, key=lambda row: row.attempt)
        episode_latency = sum(row.latency_s for row in ordered)
        outcomes.append(
            _EpisodeOutcome(
                first_passed=first_passed,
                with_retries_passed=with_retries_passed,
                latency_s=episode_latency,
            )
        )
    return outcomes


def format_summary_table(summary: Summary) -> str:
    """Render a compact human-readable summary table."""
    headers = (
        "harness",
        "N",
        "1st%",
        "w/retry%",
        "med_s",
        "p90_s",
    )
    lines = [
        " ".join(f"{header:>10}" for header in headers),
    ]
    for row in summary.by_harness:
        lines.append(
            " ".join(
                (
                    f"{row.harness:>10}",
                    f"{row.n_episodes:>10d}",
                    f"{row.first_attempt_pass_rate * 100:>9.1f}%",
                    f"{row.with_retries_pass_rate * 100:>9.1f}%",
                    f"{row.median_latency_s:>10.2f}",
                    f"{row.p90_latency_s:>10.2f}",
                )
            )
        )
    return "\n".join(lines)


def summary_to_json(summary: Summary) -> str:
    """Serialize summary for machine consumption."""
    payload = {
        "retries": summary.retries,
        "by_harness": [asdict(row) for row in summary.by_harness],
    }
    return json.dumps(payload, indent=2)


def format_benchmark_markdown_table(summary: Summary) -> str:
    """Render a Markdown table suitable for pasting into docs/BENCHMARKS.md."""
    header = (
        "| Harness | N | First-attempt % | With-retries % | Median latency (s) | P90 latency (s) |"
    )
    separator = "| --- | ---: | ---: | ---: | ---: | ---: |"
    rows = [
        (
            f"| {row.harness} | {row.n_episodes} | "
            f"{row.first_attempt_pass_rate * 100:.1f} | "
            f"{row.with_retries_pass_rate * 100:.1f} | "
            f"{row.median_latency_s:.2f} | {row.p90_latency_s:.2f} |"
        )
        for row in summary.by_harness
    ]
    return "\n".join([header, separator, *rows])
