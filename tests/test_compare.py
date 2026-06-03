"""Tests for eval/compare.py inventory fact extraction and matching."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from eval.compare import (
    InventoryFacts,
    _load_baseline,
    compare_inventory_facts,
    evaluate_inventory_answer,
    extract_answer_facts,
    extract_baseline_facts,
)
from eval.compare import (
    main as compare_main,
)

EXAMPLE_BASELINE_PATH = Path("eval/fixtures/example/inventory.json")


@pytest.fixture
def example_baseline() -> dict[str, object]:
    """Load the committed synthetic inventory fixture."""
    return json.loads(EXAMPLE_BASELINE_PATH.read_text(encoding="utf-8"))


@pytest.fixture
def baseline_facts(example_baseline: dict[str, object]) -> InventoryFacts:
    return extract_baseline_facts(example_baseline)


def test_extract_baseline_facts_from_example_fixture(
    example_baseline: dict[str, object],
) -> None:
    facts = extract_baseline_facts(example_baseline)
    assert facts.pipe_count == 3
    assert facts.pipe_names == (
        "Onboarding Requests",
        "IT Helpdesk",
        "Procurement",
    )


def test_exact_match_passes(example_baseline: dict[str, object]) -> None:
    answer = (
        "You have access to 3 pipes in Acme Demo Org:\n"
        "- Onboarding Requests\n"
        "- IT Helpdesk\n"
        "- Procurement\n"
    )
    assert evaluate_inventory_answer(example_baseline, answer) is True


def test_missing_pipe_fails(example_baseline: dict[str, object]) -> None:
    answer = "You have access to 3 pipes:\n- Onboarding Requests\n- IT Helpdesk\n"
    assert evaluate_inventory_answer(example_baseline, answer) is False


def test_count_mismatch_fails(example_baseline: dict[str, object]) -> None:
    answer = "You have access to 5 pipes:\n- Onboarding Requests\n- IT Helpdesk\n- Procurement\n"
    assert evaluate_inventory_answer(example_baseline, answer) is False


def test_case_insensitive_substring_match(example_baseline: dict[str, object]) -> None:
    answer = "found 3 pipes: onboarding requests, it helpdesk, procurement."
    assert evaluate_inventory_answer(example_baseline, answer) is True


def test_extract_answer_facts_reports_matched_names(baseline_facts: InventoryFacts) -> None:
    answer = "3 pipes including IT Helpdesk and procurement"
    facts = extract_answer_facts(answer, baseline_facts.pipe_names)
    assert facts.pipe_count == 3
    assert "IT Helpdesk" in facts.pipe_names
    assert "Procurement" in facts.pipe_names
    assert "Onboarding Requests" not in facts.pipe_names


def test_compare_inventory_facts_requires_full_name_set() -> None:
    baseline = extract_baseline_facts(
        {"organizations": [{"pipes": [{"name": "Alpha"}, {"name": "Beta"}], "pipesCount": 2}]}
    )
    partial_answer = extract_answer_facts("2 pipes: Alpha", baseline.pipe_names)
    assert compare_inventory_facts(baseline, partial_answer) is False


def test_truncated_baseline_uses_listed_pipe_count_not_pipes_count() -> None:
    """CLI may report org-wide pipesCount while pipes[] is a truncated page."""
    payload = {
        "organizations": [
            {
                "pipes": [{"name": "Alpha"}, {"name": "Beta"}],
                "pipesCount": 274,
                "pipes_truncated": True,
            }
        ],
        "search_limits": {"pipes_truncated": True},
    }
    facts = extract_baseline_facts(payload)
    assert facts.pipe_count == 2
    assert facts.pipe_names == ("Alpha", "Beta")


def test_truncated_baseline_passes_when_answer_lists_visible_pipes() -> None:
    payload = {
        "organizations": [
            {
                "pipes": [{"name": "Alpha"}, {"name": "Beta"}],
                "pipesCount": 274,
                "pipes_truncated": True,
            }
        ],
        "search_limits": {"pipes_truncated": True},
    }
    answer = "Visible pipes (2): Alpha and Beta."
    assert evaluate_inventory_answer(payload, answer) is True


def test_answer_prefers_count_matching_truncated_baseline_when_both_cited() -> None:
    payload = {
        "organizations": [
            {
                "pipes": [{"name": "Alpha"}, {"name": "Beta"}],
                "pipesCount": 274,
                "pipes_truncated": True,
            }
        ],
        "search_limits": {"pipes_truncated": True},
    }
    answer = "You have access to 2 pipes in this org (274 pipes org-wide total): Alpha and Beta."
    assert evaluate_inventory_answer(payload, answer) is True


def test_token_fallback_matches_slightly_wrong_pipe_label() -> None:
    payload = {
        "organizations": [
            {
                "pipes": [{"name": "[Template] Team Task Management"}],
                "pipesCount": 1,
            }
        ]
    }
    answer = "1 pipe: [Templates] Team Task Management → 0 open cards"
    assert evaluate_inventory_answer(payload, answer) is True


def test_truncated_baseline_fails_when_answer_claims_org_total_count() -> None:
    payload = {
        "organizations": [
            {
                "pipes": [{"name": "Alpha"}, {"name": "Beta"}],
                "pipesCount": 274,
                "pipes_truncated": True,
            }
        ],
        "search_limits": {"pipes_truncated": True},
    }
    answer = "You have 274 pipes including Alpha and Beta."
    assert evaluate_inventory_answer(payload, answer) is False


def test_extract_baseline_facts_from_bare_pipe_list() -> None:
    payload = [{"name": "Alpha"}, {"name": "Beta"}, {"name": "Gamma"}]
    facts = extract_baseline_facts(payload)
    assert facts.pipe_count == 3
    assert facts.pipe_names == ("Alpha", "Beta", "Gamma")


def test_extract_baseline_facts_invalid_raises_value_error() -> None:
    with pytest.raises(ValueError, match="organizations"):
        extract_baseline_facts({"unexpected": "shape"})


def test_cli_main_passes_with_matching_answer(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text(EXAMPLE_BASELINE_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    answer_path = tmp_path / "answer.txt"
    answer_path.write_text(
        "You have access to 3 pipes:\n- Onboarding Requests\n- IT Helpdesk\n- Procurement\n",
        encoding="utf-8",
    )

    exit_code = compare_main(["--baseline", str(baseline_path), "--answer", str(answer_path)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "✓" in captured.out


def test_cli_main_fails_with_mismatched_answer(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text(EXAMPLE_BASELINE_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    answer_path = tmp_path / "answer.txt"
    answer_path.write_text("You have access to 1 pipe: Onboarding Requests\n", encoding="utf-8")

    exit_code = compare_main(["--baseline", str(baseline_path), "--answer", str(answer_path)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "✗" in captured.out


def test_extract_baseline_facts_skips_non_dict_orgs() -> None:
    payload = {
        "organizations": [
            "not-an-org",
            {"pipes": [{"name": "Alpha"}], "pipesCount": 1},
        ],
    }
    facts = extract_baseline_facts(payload)
    assert facts.pipe_names == ("Alpha",)
    assert facts.pipe_count == 1


def test_extract_baseline_facts_org_without_pipes_list() -> None:
    payload = {"organizations": [{"pipesCount": 3}]}
    facts = extract_baseline_facts(payload)
    assert facts.pipe_count == 3
    assert facts.pipe_names == ()


def test_extract_baseline_facts_empty_pipes_list_uses_declared_count() -> None:
    payload = {"organizations": [{"pipes": [], "pipesCount": 5}]}
    facts = extract_baseline_facts(payload)
    assert facts.pipe_count == 5
    assert facts.pipe_names == ()


def test_extract_baseline_facts_zero_declared_and_listed_count() -> None:
    payload = {"organizations": [{"pipes": [], "pipesCount": 0}]}
    facts = extract_baseline_facts(payload)
    assert facts.pipe_count == 0


def test_extract_baseline_facts_uses_listed_count_when_declared_missing() -> None:
    payload = {"organizations": [{"pipes": [{"name": "Alpha"}, {"name": "Beta"}]}]}
    facts = extract_baseline_facts(payload)
    assert facts.pipe_count == 2
    assert facts.pipe_names == ("Alpha", "Beta")


def test_extract_baseline_facts_ignores_negative_pipes_count() -> None:
    payload = {"organizations": [{"pipes": [{"name": "Alpha"}], "pipesCount": -1}]}
    facts = extract_baseline_facts(payload)
    assert facts.pipe_count == 1


def test_extract_baseline_facts_skips_invalid_pipe_entries() -> None:
    payload = [
        "not-a-pipe",
        {"name": ""},
        {"name": "   "},
        {"no_name": "X"},
        {"name": "Valid"},
    ]
    facts = extract_baseline_facts(payload)
    assert facts.pipe_names == ("Valid",)
    assert facts.pipe_count == 1


def test_truncated_baseline_detected_via_org_flag_only() -> None:
    payload = {
        "organizations": [
            {"pipes": [{"name": "Alpha"}], "pipesCount": 50, "pipes_truncated": True},
        ],
    }
    facts = extract_baseline_facts(payload)
    assert facts.pipe_count == 1


def test_truncated_baseline_inferred_when_declared_exceeds_listed() -> None:
    payload = {
        "organizations": [
            {"pipes": [{"name": "Alpha"}, {"name": "Beta"}], "pipesCount": 100},
        ],
    }
    facts = extract_baseline_facts(payload)
    assert facts.pipe_count == 2


def test_load_baseline_invalid_json_root_raises(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text("42", encoding="utf-8")
    with pytest.raises(ValueError, match="object or array"):
        _load_baseline(path)


def test_compare_inventory_facts_infers_count_from_names() -> None:
    baseline = InventoryFacts(pipe_count=0, pipe_names=("Alpha", "Beta"))
    answer = InventoryFacts(pipe_count=0, pipe_names=("Alpha", "Beta"))
    assert compare_inventory_facts(baseline, answer) is True


def test_extract_answer_facts_returns_zero_count_when_unstated(
    baseline_facts: InventoryFacts,
) -> None:
    facts = extract_answer_facts("Onboarding Requests only", baseline_facts.pipe_names)
    assert facts.pipe_count == 0
    assert "Onboarding Requests" in facts.pipe_names


def test_compare_script_entry_point(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text(EXAMPLE_BASELINE_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    answer_path = tmp_path / "answer.txt"
    answer_path.write_text(
        "You have access to 3 pipes:\n- Onboarding Requests\n- IT Helpdesk\n- Procurement\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "eval" / "compare.py"),
            "--baseline",
            str(baseline_path),
            "--answer",
            str(answer_path),
        ],
        check=False,
        capture_output=True,
        text=True,
        cwd=repo_root,
    )

    assert result.returncode == 0
    assert "✓" in result.stdout


def test_compare_main_block(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import runpy

    repo_root = Path(__file__).resolve().parents[1]
    script_path = repo_root / "eval" / "compare.py"
    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text(EXAMPLE_BASELINE_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    answer_path = tmp_path / "answer.txt"
    answer_path.write_text(
        "You have access to 3 pipes:\n- Onboarding Requests\n- IT Helpdesk\n- Procurement\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            str(script_path),
            "--baseline",
            str(baseline_path),
            "--answer",
            str(answer_path),
        ],
    )

    with pytest.raises(SystemExit) as exc_info:
        runpy.run_path(str(script_path), run_name="__main__")

    assert exc_info.value.code == 0
