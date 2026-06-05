"""Offline tests for eval/bundle_nat_profile.py."""

from __future__ import annotations

import json
from pathlib import Path

from eval.bundle_nat_profile import bundle_nat_profile


def _write_profiler_run_dir(run_dir: Path) -> None:
    run_dir.mkdir()
    (run_dir / "workflow_profiling_metrics.json").write_text(
        json.dumps({"nested_stack_analysis": {"score": 1}}),
        encoding="utf-8",
    )
    (run_dir / "inference_optimization.json").write_text(
        json.dumps(
            {
                "workflow_runtimes": [12.5],
                "confidence_intervals": {
                    "workflow_run_time_confidence_intervals": {
                        "mean": 12.5,
                        "p90": 14.0,
                        "ninetieth_interval": [11.0, 14.0],
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    (run_dir / "all_requests_profiler_traces.json").write_text(
        json.dumps([{"event_type": "LLM_START"}]),
        encoding="utf-8",
    )


def test_bundle_nat_profile_lean_default(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    _write_profiler_run_dir(run_dir)

    bundled = bundle_nat_profile(
        run_dir=run_dir,
        scenario="inventory",
        workflow_config="configs/pipefy_nat_workflow_profile.yml",
        model="meta/llama-3.1-8b-instruct",
        organization_id="900000001",
    )

    assert bundled["run"]["scenario"] == "inventory"
    assert bundled["summary"]["total_duration_s"] == 12.5
    assert bundled["summary"]["trace_step_count"] == 1
    artifacts = bundled["nat_profiler_artifacts"]
    assert artifacts["run_dir"] == str(run_dir)
    assert "workflow_profiling_metrics.json" in artifacts["files"]
    assert "workflow_profiling_metrics" not in artifacts
    assert "inference_optimization" not in artifacts
    assert "all_requests_profiler_traces" not in artifacts


def test_bundle_nat_profile_embed_artifacts(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    _write_profiler_run_dir(run_dir)

    bundled = bundle_nat_profile(
        run_dir=run_dir,
        scenario="inventory",
        workflow_config="configs/pipefy_nat_workflow_profile.yml",
        model="meta/llama-3.1-8b-instruct",
        organization_id="900000001",
        embed_artifacts=True,
    )

    artifacts = bundled["nat_profiler_artifacts"]
    assert artifacts["workflow_profiling_metrics"] == {"nested_stack_analysis": {"score": 1}}
    assert artifacts["inference_optimization"]["workflow_runtimes"] == [12.5]
    assert artifacts["all_requests_profiler_traces"] == [{"event_type": "LLM_START"}]


def test_inventory_prompt_print_path(tmp_path: Path, monkeypatch) -> None:
    from eval import inventory_prompt as mod

    prompts = tmp_path / "demos" / "prompts"
    prompts.mkdir(parents=True)
    (prompts / "inventory.txt").write_text("List pipes.", encoding="utf-8")
    monkeypatch.setattr(mod, "PROMPTS_DIR", prompts)
    missing_baseline = tmp_path / "missing.json"

    text = mod.build_inventory_eval_prompt(
        demo_org_id="42",
        live_baseline_path=missing_baseline,
    )
    assert "organization_id integer 42" in text
