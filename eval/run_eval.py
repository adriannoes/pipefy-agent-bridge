"""Evaluation runner: reliability + latency summary per harness (PRD-2 FR-2/FR-7)."""

from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

REPO_ROOT = Path(__file__).resolve().parents[1]
if __package__ is None:
    sys.path.insert(0, str(REPO_ROOT))

from eval.compare import evaluate_inventory_answer  # noqa: E402
from eval.golden_loader import GoldenCase, load_golden  # noqa: E402
from scripts.extract_nat_answer import extract_nat_answer_text  # noqa: E402

DEFAULT_GOLDEN = REPO_ROOT / "eval" / "golden.yaml"
DEFAULT_SCENARIO = "inventory"
DEFAULT_RUNS = 5
DEFAULT_RETRIES = 3
DEFAULT_TIMEOUT_S = 600.0

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


def summarize(results: list[RunResult], retries: int) -> Summary:
    """Aggregate per-harness first-attempt vs with-retries pass rates and latency percentiles.

    Episodes are grouped by ``(scenario, harness, run)``. An episode passes on first attempt
    when ``attempt == 1`` and ``passed``; it passes with retries when any attempt in
    ``1..retries`` passed.
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
        latencies = [row.latency_s for row in harness_rows]

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


@dataclass(frozen=True)
class _EpisodeOutcome:
    first_passed: bool
    with_retries_passed: bool


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
        outcomes.append(
            _EpisodeOutcome(
                first_passed=first_passed,
                with_retries_passed=with_retries_passed,
            )
        )
    return outcomes


def _load_baseline_json(path: Path) -> dict[str, Any] | list[Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, (dict, list)):
        msg = f"baseline JSON root must be object or array, got {type(payload).__name__!r}"
        raise ValueError(msg)
    return payload


def _score_inventory_answer(baseline_path: Path, answer_text: str) -> bool:
    baseline = _load_baseline_json(baseline_path)
    return evaluate_inventory_answer(baseline, answer_text)


def _invoke_harness(
    harness: HarnessName,
    *,
    scenario: str,
    repo_root: Path,
    env: dict[str, str],
    timeout_s: float,
) -> subprocess.CompletedProcess[str]:
    if harness == "cursor":
        cmd = ["make", "demo-cursor", f"SCENARIO={scenario}"]
    else:
        cmd = ["make", "demo-nat", f"SCENARIO={scenario}"]
    return subprocess.run(
        cmd,
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout_s,
        check=False,
    )


def _answer_from_harness_output(harness: HarnessName, combined_output: str) -> str:
    if harness == "cursor":
        return combined_output
    return extract_nat_answer_text(combined_output)


def run_episode_attempt(
    harness: HarnessName,
    *,
    scenario: str,
    case: GoldenCase,
    repo_root: Path,
    env: dict[str, str],
    timeout_s: float,
) -> tuple[bool, float]:
    """Invoke harness once; return (passed, latency_s)."""
    started = time.perf_counter()
    try:
        completed = _invoke_harness(
            harness,
            scenario=scenario,
            repo_root=repo_root,
            env=env,
            timeout_s=timeout_s,
        )
    except subprocess.TimeoutExpired:
        return False, time.perf_counter() - started

    latency_s = time.perf_counter() - started
    combined = (completed.stdout or "") + (completed.stderr or "")
    if completed.returncode != 0:
        return False, latency_s

    answer = _answer_from_harness_output(harness, combined)
    if not answer.strip():
        return False, latency_s

    passed = _score_inventory_answer(case.baseline, answer)
    return passed, latency_s


def execute_eval(
    cases: list[GoldenCase],
    *,
    harnesses: tuple[HarnessName, ...],
    runs: int,
    retries: int,
    repo_root: Path,
    env: dict[str, str] | None = None,
    timeout_s: float = DEFAULT_TIMEOUT_S,
) -> list[RunResult]:
    """Run all episodes and return per-attempt results."""
    if runs < 1:
        msg = f"runs must be >= 1, got {runs!r}"
        raise ValueError(msg)

    run_env = dict(os.environ if env is None else env)
    results: list[RunResult] = []

    for case in cases:
        for harness in harnesses:
            for run_index in range(1, runs + 1):
                for attempt in range(1, retries + 1):
                    passed, latency_s = run_episode_attempt(
                        harness,
                        scenario=case.scenario,
                        case=case,
                        repo_root=repo_root,
                        env=run_env,
                        timeout_s=timeout_s,
                    )
                    results.append(
                        RunResult(
                            scenario=case.scenario,
                            harness=harness,
                            run=run_index,
                            attempt=attempt,
                            passed=passed,
                            latency_s=latency_s,
                        )
                    )
                    if passed:
                        break

    return results


def _parse_harness(value: str) -> tuple[HarnessName, ...]:
    normalized = value.strip().lower()
    if normalized == "both":
        return ("cursor", "nat")
    if normalized in ("cursor", "nat"):
        return (normalized,)  # type: ignore[return-value]
    msg = f"invalid --harness {value!r}: expected 'cursor', 'nat', or 'both', got {value!r}"
    raise argparse.ArgumentTypeError(msg)


def _filter_cases(cases: list[GoldenCase], scenario: str) -> list[GoldenCase]:
    filtered = [case for case in cases if case.scenario == scenario]
    if not filtered:
        known = ", ".join(sorted({case.scenario for case in cases}))
        msg = (
            f"no golden case for scenario {scenario!r}; available scenario(s): {known or '(none)'}"
        )
        raise SystemExit(msg)
    return filtered


def _build_env(*, model: str | None) -> dict[str, str]:
    run_env = dict(os.environ)
    if model:
        run_env["NIM_MODEL"] = model
    return run_env


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


def build_parser() -> argparse.ArgumentParser:
    """CLI argument parser for the evaluation runner."""
    parser = argparse.ArgumentParser(
        description="Run golden scenarios N times per harness; report reliability and latency.",
    )
    parser.add_argument(
        "--golden",
        type=Path,
        default=DEFAULT_GOLDEN,
        help=f"Path to golden.yaml (default: {DEFAULT_GOLDEN.relative_to(REPO_ROOT)})",
    )
    parser.add_argument(
        "--scenario",
        default=DEFAULT_SCENARIO,
        help=f"Scenario name to evaluate (default: {DEFAULT_SCENARIO})",
    )
    parser.add_argument(
        "--harness",
        default="both",
        help="Harness to run: cursor, nat, or both (default: both)",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=DEFAULT_RUNS,
        metavar="N",
        help=f"Independent run episodes per harness (default: {DEFAULT_RUNS})",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Set NIM_MODEL for NAT harness runs (e.g. meta/llama-3.1-70b-instruct)",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=DEFAULT_RETRIES,
        help=f"Max attempts per episode for with-retries metric (default: {DEFAULT_RETRIES})",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_S,
        metavar="SECONDS",
        help=f"Subprocess timeout per harness attempt (default: {DEFAULT_TIMEOUT_S:.0f})",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print summary JSON after the table",
    )
    parser.add_argument(
        "--emit-markdown",
        action="store_true",
        help="Print a Markdown results table for docs/BENCHMARKS.md",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry: load golden cases, run harnesses, print summary."""
    parser = build_parser()
    args = parser.parse_args(argv)

    cases = _filter_cases(load_golden(args.golden), args.scenario)
    unsupported = [case.scenario for case in cases if case.scenario != "inventory"]
    if unsupported:
        names = ", ".join(sorted(set(unsupported)))
        msg = f"run_eval currently supports only 'inventory' scoring, got scenario(s): {names}"
        print(msg, file=sys.stderr)
        return 2

    harnesses = _parse_harness(args.harness)
    results = execute_eval(
        cases,
        harnesses=harnesses,
        runs=args.runs,
        retries=args.retries,
        repo_root=REPO_ROOT,
        env=_build_env(model=args.model),
        timeout_s=args.timeout,
    )
    summary = summarize(results, args.retries)
    print(format_summary_table(summary))
    if args.json:
        print(summary_to_json(summary))
    if args.emit_markdown:
        print()
        print(format_benchmark_markdown_table(summary))
    return 0


if __name__ == "__main__":
    sys.exit(main())
