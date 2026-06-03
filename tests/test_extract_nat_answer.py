"""Tests for scripts/extract_nat_answer.py."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.extract_nat_answer import (
    _extract_workflow_result_block,
    extract_nat_answer_text,
)
from scripts.extract_nat_answer import (
    main as extract_main,
)


def test_extract_skips_tool_call_workflow_result() -> None:
    raw = """
Workflow Result:
{"name": "pipefy__search_pipes", "parameters": {"organization_id": 1}}
--------------------------------------------------
Final Answer: 5 pipes: Reimbursement → 8, Analytics → 0
"""
    result = extract_nat_answer_text(raw)
    assert "Reimbursement" in result
    assert "pipefy__search_pipes" not in result


def test_extract_uses_last_workflow_result_block() -> None:
    raw = """
------------------------------
Workflow Result:
partial → 1
--------------------------------------------------
some tool noise
---
Workflow Result:
Reimbursement → 8
Analytics → 0
--------------------------------------------------
"""
    assert "Reimbursement" in extract_nat_answer_text(raw)
    assert "Analytics" in extract_nat_answer_text(raw)
    assert "partial" not in extract_nat_answer_text(raw)


def test_extract_prefers_last_non_empty_final_answer() -> None:
    raw = "Final Answer: Real answer text\n---\nFinal Answer:   "
    assert extract_nat_answer_text(raw) == "Real answer text"


def test_extract_final_answer_when_no_workflow_result() -> None:
    raw = """
tool: list_pipes
partial answer
Final Answer: You have 2 pipes: Alpha and Beta.
---
more noise
Final Answer: You have 3 pipes: Alpha, Beta, and Gamma.
"""
    result = extract_nat_answer_text(raw)
    assert "Gamma" in result
    assert "3 pipes" in result
    assert "partial answer" not in result


def test_extract_strips_ansi_escape_sequences() -> None:
    raw = "\x1b[1mFinal Answer:\x1b[0m \x1b[32mHello world\x1b[0m"
    assert extract_nat_answer_text(raw) == "Hello world"


def test_extract_fallback_uses_last_substantial_lines() -> None:
    lines = [f"line-{i}" for i in range(50)]
    raw = "\n".join(lines)
    result = extract_nat_answer_text(raw)
    assert "line-49" in result
    assert "line-0" not in result


def test_extract_empty_string_returns_empty() -> None:
    assert extract_nat_answer_text("") == ""


def test_extract_whitespace_only_returns_empty() -> None:
    assert extract_nat_answer_text("  \n\t\n  ") == ""


def test_extract_workflow_result_block_no_marker() -> None:
    assert _extract_workflow_result_block("tool noise only") == ""


def test_extract_workflow_result_block_stops_at_separator() -> None:
    raw = "Workflow Result:\nLine one\nLine two\n---\nignored"
    assert _extract_workflow_result_block(raw) == "Line one\nLine two"


def test_extract_final_answer_single_line() -> None:
    raw = "tool noise\nFinal Answer: Single line answer."
    assert extract_nat_answer_text(raw) == "Single line answer."


def test_extract_nat_answer_cli_main(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    input_path = tmp_path / "stdout.txt"
    input_path.write_text("Final Answer: CLI extracted text\n", encoding="utf-8")

    exit_code = extract_main([str(input_path)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out.strip() == "CLI extracted text"
