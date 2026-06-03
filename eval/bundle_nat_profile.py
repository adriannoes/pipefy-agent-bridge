"""Bundle NAT profiler artifacts from a nat eval output_dir into one JSON file."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_ARTIFACT_NAMES = (
    "workflow_profiling_metrics.json",
    "inference_optimization.json",
    "all_requests_profiler_traces.json",
    "standardized_data_all.csv",
    "workflow_profiling_report.txt",
)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _summary_from_nat(
    *,
    inference_optimization: dict[str, Any] | None,
    workflow_metrics: dict[str, Any] | None,
    traces: list[Any] | None,
) -> dict[str, Any]:
    total_duration_s: float | None = None
    if inference_optimization:
        runtimes = inference_optimization.get("workflow_runtimes")
        if isinstance(runtimes, list) and runtimes:
            total_duration_s = float(runtimes[0])
        elif isinstance(runtimes, (int, float)):
            total_duration_s = float(runtimes)
    workflow_runtime: dict[str, Any] = {}
    if inference_optimization:
        ci = inference_optimization.get("confidence_intervals") or {}
        wf_ci = ci.get("workflow_run_time_confidence_intervals") or {}
        if isinstance(wf_ci, dict):
            workflow_runtime = {
                "mean_s": wf_ci.get("mean"),
                "p90_s": wf_ci.get("p90"),
                "confidence_interval_90_s": wf_ci.get("ninetieth_interval"),
            }
    trace_step_count = len(traces) if isinstance(traces, list) else None
    return {
        "total_duration_s": total_duration_s,
        "agent_iteration_count": None,
        "trace_step_count": trace_step_count,
        "tool_call_count": None,
        "llm_invocation_count": None,
        "workflow_runtime": workflow_runtime,
        "workflow_profiling_metrics_present": workflow_metrics is not None,
    }


def bundle_nat_profile(
    *,
    run_dir: Path,
    scenario: str,
    workflow_config: str,
    model: str,
    organization_id: str,
) -> dict[str, Any]:
    """Assemble a single JSON document from NAT profiler files in *run_dir*."""
    nat_files: dict[str, str] = {}
    loaded: dict[str, Any] = {}
    for name in _ARTIFACT_NAMES:
        path = run_dir / name
        if path.is_file():
            nat_files[name] = str(path.relative_to(run_dir))
            if name.endswith(".json"):
                loaded[name.removesuffix(".json")] = _read_json(path)

    inference = loaded.get("inference_optimization")
    metrics = loaded.get("workflow_profiling_metrics")
    traces = loaded.get("all_requests_profiler_traces")

    return {
        "captured_at": datetime.now(tz=UTC).isoformat(),
        "run": {
            "scenario": scenario,
            "harness": "nat",
            "workflow_config": workflow_config,
            "model": model,
            "organization_id": organization_id,
        },
        "summary": _summary_from_nat(
            inference_optimization=inference if isinstance(inference, dict) else None,
            workflow_metrics=metrics if isinstance(metrics, dict) else None,
            traces=traces if isinstance(traces, list) else None,
        ),
        "nat_profiler_artifacts": {
            "run_dir": str(run_dir),
            "files": nat_files,
            "workflow_profiling_metrics": metrics,
            "inference_optimization": inference,
            "all_requests_profiler_traces": traces,
        },
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True, help="nat eval output_dir")
    parser.add_argument("--out", type=Path, required=True, help="eval/profiles/<timestamp>.json")
    parser.add_argument("--scenario", default="inventory")
    parser.add_argument(
        "--workflow-config",
        default="configs/pipefy_nat_workflow_profile.yml",
    )
    parser.add_argument("--model", default="meta/llama-3.1-8b-instruct")
    parser.add_argument("--organization-id", default="")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if not args.run_dir.is_dir():
        print(f"error: run dir not found: {args.run_dir}", file=sys.stderr)
        return 1
    payload = bundle_nat_profile(
        run_dir=args.run_dir,
        scenario=args.scenario,
        workflow_config=args.workflow_config,
        model=args.model,
        organization_id=args.organization_id,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if not payload["nat_profiler_artifacts"]["files"]:
        print(
            f"warning: no NAT profiler artifacts in {args.run_dir} "
            "(is eval.general.profiler enabled and nvidia-nat-profiler installed?)",
            file=sys.stderr,
        )
        return 2
    print(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
