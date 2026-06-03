"""Offline tests for eval/bundle_nat_profile.py."""

from __future__ import annotations

import json
from pathlib import Path

from eval.bundle_nat_profile import bundle_nat_profile


def test_bundle_nat_profile_merges_artifacts(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
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

    bundled = bundle_nat_profile(
        run_dir=run_dir,
        scenario="inventory",
        workflow_config="configs/pipefy_nat_workflow_profile.yml",
        model="meta/llama-3.1-8b-instruct",
        organization_id="900000001",
    )

    assert bundled["run"]["scenario"] == "inventory"
    assert bundled["summary"]["total_duration_s"] == 12.5
    artifacts = bundled["nat_profiler_artifacts"]
    assert "workflow_profiling_metrics.json" in artifacts["files"]
    assert artifacts["workflow_profiling_metrics"] == {"nested_stack_analysis": {"score": 1}}


def test_build_inventory_eval_prompt_uses_demo_org(tmp_path: Path, monkeypatch) -> None:
    from eval import nat_inventory_eval_prompt as prompt_mod

    prompts = tmp_path / "demos" / "prompts"
    prompts.mkdir(parents=True)
    (prompts / "inventory.txt").write_text("List pipes.", encoding="utf-8")
    monkeypatch.setattr(prompt_mod, "_PROMPTS_DIR", prompts)
    monkeypatch.setattr(prompt_mod, "_LIVE_BASELINE", tmp_path / "missing.json")

    text = prompt_mod.build_inventory_eval_prompt(demo_org_id="42")
    assert "organization_id integer 42" in text
    assert "List pipes." in text
