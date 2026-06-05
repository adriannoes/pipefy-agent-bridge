"""Offline tests for eval/inventory_prompt.py."""

from __future__ import annotations

from pathlib import Path

from eval.inventory_prompt import build_inventory_eval_prompt


def test_build_inventory_eval_prompt_uses_demo_org_when_no_live_baseline(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from eval import inventory_prompt as prompt_mod

    prompts = tmp_path / "demos" / "prompts"
    prompts.mkdir(parents=True)
    (prompts / "inventory.txt").write_text("List pipes.", encoding="utf-8")
    missing_live = tmp_path / "missing-live.json"

    monkeypatch.setattr(prompt_mod, "PROMPTS_DIR", prompts)
    monkeypatch.setattr(
        prompt_mod,
        "scoring_baseline_path",
        lambda _scenario: missing_live,
    )

    text = build_inventory_eval_prompt(demo_org_id="42", live_baseline_path=missing_live)
    assert "organization_id integer 42" in text
    assert "List pipes." in text
    assert "Use each id field from the search_pipes" in text


def test_build_inventory_eval_prompt_uses_live_org_and_pipe_ids(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from eval import inventory_prompt as prompt_mod

    prompts = tmp_path / "demos" / "prompts"
    prompts.mkdir(parents=True)
    (prompts / "inventory.txt").write_text("List pipes.", encoding="utf-8")
    live = tmp_path / "inventory.json"
    live.write_text(
        """
        {
          "organizations": [{
            "id": "777",
            "pipes": [{"id": "101", "name": "Alpha"}, {"id": "102", "name": "Beta"}]
          }]
        }
        """.strip(),
        encoding="utf-8",
    )

    monkeypatch.setattr(prompt_mod, "PROMPTS_DIR", prompts)

    text = build_inventory_eval_prompt(demo_org_id="42", live_baseline_path=live)
    assert "organization_id integer 777" in text
    assert "101, 102" in text
