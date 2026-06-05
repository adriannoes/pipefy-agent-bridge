"""Evaluation runner: reliability + latency summary per harness."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if __package__ is None:
    sys.path.insert(0, str(REPO_ROOT))

from eval.compare import evaluate_answer, load_baseline  # noqa: E402
from eval.eval_summary import (  # noqa: E402
    HarnessName,
    RunResult,
    format_benchmark_markdown_table,
    format_summary_table,
    summarize,
    summary_to_json,
)
from eval.golden_loader import GoldenCase, load_golden  # noqa: E402
from eval.ground_truth_refresh import refresh_ground_truth, scoring_baseline_path  # noqa: E402
from scripts.extract_nat_answer import extract_nat_answer_text  # noqa: E402

DEFAULT_GOLDEN = REPO_ROOT / "eval" / "golden.yaml"
DEFAULT_SCENARIO = "inventory"
DEFAULT_RUNS = 5
DEFAULT_RETRIES = 3
DEFAULT_TIMEOUT_S = 600.0


def _score_answer(scenario: str, baseline_path: Path, answer_text: str) -> bool:
    baseline = load_baseline(baseline_path)
    return evaluate_answer(baseline, answer_text, scenario=scenario)


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
    scoring_baseline: Path,
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

    passed = _score_answer(scenario, scoring_baseline, answer)
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
    skip_ground_truth: bool = False,
) -> list[RunResult]:
    """Run all episodes and return per-attempt results."""
    if runs < 1:
        msg = f"runs must be >= 1, got {runs!r}"
        raise ValueError(msg)

    run_env = dict(os.environ if env is None else env)
    results: list[RunResult] = []
    scoring_baselines: dict[str, Path] = {}

    for case in cases:
        if case.scenario not in scoring_baselines:
            if not skip_ground_truth:
                refresh_ground_truth(case.scenario, repo_root=repo_root)
            live_path = scoring_baseline_path(case.scenario)
            if not live_path.is_file():
                msg = (
                    f"scoring baseline missing for scenario {case.scenario!r}: {live_path!s} "
                    f"(run ./eval/ground_truth.sh {case.scenario} or omit --skip-ground-truth)"
                )
                raise FileNotFoundError(msg)
            scoring_baselines[case.scenario] = live_path.resolve()

    for case in cases:
        scoring_baseline = scoring_baselines[case.scenario]
        for harness in harnesses:
            for run_index in range(1, runs + 1):
                for attempt in range(1, retries + 1):
                    passed, latency_s = run_episode_attempt(
                        harness,
                        scenario=case.scenario,
                        scoring_baseline=scoring_baseline,
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
    if normalized == "cursor":
        return ("cursor",)
    if normalized == "nat":
        return ("nat",)
    msg = f"invalid --harness {value!r}: expected 'cursor', 'nat', or 'both', got {value!r}"
    raise argparse.ArgumentTypeError(msg)


def _filter_cases(cases: list[GoldenCase], scenario: str) -> list[GoldenCase]:
    normalized = scenario.strip().lower()
    if normalized == "all":
        return cases
    filtered = [case for case in cases if case.scenario == scenario]
    if not filtered:
        known = ", ".join(sorted({case.scenario for case in cases}))
        msg = (
            f"no golden case for scenario {scenario!r}; available scenario(s): "
            f"{known or '(none)'} (use 'all' to run every golden case)"
        )
        raise SystemExit(msg)
    return filtered


def _build_env(*, model: str | None) -> dict[str, str]:
    run_env = dict(os.environ)
    if model:
        run_env["NIM_MODEL"] = model
    return run_env


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
        help=(
            f"Scenario to evaluate, or 'all' for every golden case (default: {DEFAULT_SCENARIO})"
        ),
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
        "--skip-ground-truth",
        action="store_true",
        help="Skip ground_truth.sh refresh; score against existing eval/fixtures/live/*.json",
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

    harnesses = _parse_harness(args.harness)
    try:
        results = execute_eval(
            cases,
            harnesses=harnesses,
            runs=args.runs,
            retries=args.retries,
            repo_root=REPO_ROOT,
            env=_build_env(model=args.model),
            timeout_s=args.timeout,
            skip_ground_truth=args.skip_ground_truth,
        )
    except (RuntimeError, FileNotFoundError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

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
