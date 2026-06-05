"""Offline tests for eval/eval_summary.py aggregation."""

from __future__ import annotations

import pytest

from eval.eval_summary import (
    RunResult,
    format_benchmark_markdown_table,
    percentile,
    summarize,
)


def _row(
    *,
    harness: str = "nat",
    scenario: str = "inventory",
    run: int = 1,
    attempt: int = 1,
    passed: bool,
    latency_s: float,
) -> RunResult:
    return RunResult(
        scenario=scenario,
        harness=harness,  # type: ignore[arg-type]
        run=run,
        attempt=attempt,
        passed=passed,
        latency_s=latency_s,
    )


def test_summarize_all_pass_first_attempt() -> None:
    results = [
        _row(run=1, attempt=1, passed=True, latency_s=10.0),
        _row(run=2, attempt=1, passed=True, latency_s=20.0),
        _row(run=3, attempt=1, passed=True, latency_s=30.0),
    ]
    summary = summarize(results, retries=3)
    nat = summary.by_harness[0]
    assert nat.n_episodes == 3
    assert nat.first_attempt_pass_rate == 1.0
    assert nat.with_retries_pass_rate == 1.0
    assert nat.median_latency_s == 20.0
    assert nat.p90_latency_s == pytest.approx(28.0)


def test_summarize_all_fail() -> None:
    results = [
        _row(run=1, attempt=1, passed=False, latency_s=5.0),
        _row(run=1, attempt=2, passed=False, latency_s=6.0),
        _row(run=1, attempt=3, passed=False, latency_s=7.0),
        _row(run=2, attempt=1, passed=False, latency_s=8.0),
        _row(run=2, attempt=2, passed=False, latency_s=9.0),
    ]
    summary = summarize(results, retries=3)
    nat = summary.by_harness[0]
    assert nat.n_episodes == 2
    assert nat.first_attempt_pass_rate == 0.0
    assert nat.with_retries_pass_rate == 0.0
    assert nat.median_latency_s == pytest.approx(17.5)
    assert nat.p90_latency_s == pytest.approx(17.9, rel=1e-2)


def test_summarize_mixed_first_fail_second_pass() -> None:
    results = [
        _row(run=1, attempt=1, passed=False, latency_s=12.0),
        _row(run=1, attempt=2, passed=True, latency_s=18.0),
    ]
    summary = summarize(results, retries=3)
    nat = summary.by_harness[0]
    assert nat.n_episodes == 1
    assert nat.first_attempt_pass_rate == 0.0
    assert nat.with_retries_pass_rate == 1.0
    assert nat.median_latency_s == pytest.approx(30.0)


def test_summarize_latency_percentiles() -> None:
    results = [
        _row(run=1, attempt=1, passed=True, latency_s=1.0),
        _row(run=2, attempt=1, passed=True, latency_s=2.0),
        _row(run=3, attempt=1, passed=True, latency_s=3.0),
        _row(run=4, attempt=1, passed=True, latency_s=4.0),
        _row(run=5, attempt=1, passed=True, latency_s=100.0),
    ]
    summary = summarize(results, retries=1)
    nat = summary.by_harness[0]
    assert nat.median_latency_s == 3.0
    assert nat.p90_latency_s == pytest.approx(61.6, rel=1e-3)


def test_percentile_empty() -> None:
    assert percentile([], 90.0) == 0.0


def test_summarize_invalid_retries() -> None:
    with pytest.raises(ValueError, match=r"retries must be >= 1"):
        summarize([], retries=0)


def test_format_benchmark_markdown_table() -> None:
    results = [
        _row(harness="cursor", run=1, attempt=1, passed=True, latency_s=10.0),
        _row(harness="nat", run=1, attempt=1, passed=False, latency_s=20.0),
        _row(harness="nat", run=1, attempt=2, passed=True, latency_s=30.0),
    ]
    summary = summarize(results, retries=3)
    md = format_benchmark_markdown_table(summary)
    assert "| Scenario | Harness | N |" in md
    assert "| inventory | cursor | 1 | 100.0 | 100.0 |" in md
    assert "| inventory | nat | 1 | 0.0 | 100.0 |" in md


def test_format_benchmark_markdown_table_multiple_scenarios() -> None:
    results = [
        _row(scenario="inventory", harness="nat", run=1, attempt=1, passed=True, latency_s=5.0),
        _row(scenario="summary", harness="nat", run=1, attempt=1, passed=False, latency_s=15.0),
    ]
    summary = summarize(results, retries=1)
    md = format_benchmark_markdown_table(summary)
    assert "| inventory | nat | 1 | 100.0 | 100.0 |" in md
    assert "| summary | nat | 1 | 0.0 | 0.0 |" in md


def test_summarize_both_harnesses() -> None:
    results = [
        _row(harness="cursor", run=1, attempt=1, passed=True, latency_s=5.0),
        _row(harness="nat", run=1, attempt=1, passed=False, latency_s=15.0),
        _row(harness="nat", run=1, attempt=2, passed=True, latency_s=25.0),
    ]
    summary = summarize(results, retries=3)
    assert len(summary.by_harness) == 2
    cursor = next(row for row in summary.by_harness if row.harness == "cursor")
    nat = next(row for row in summary.by_harness if row.harness == "nat")
    assert cursor.first_attempt_pass_rate == 1.0
    assert nat.first_attempt_pass_rate == 0.0
    assert nat.with_retries_pass_rate == 1.0
    assert nat.median_latency_s == pytest.approx(40.0)
