#!/usr/bin/env python3
"""Extract agent Final Answer text from noisy ``nat run`` stdout for eval/compare.py."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

_ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*m")
_FINAL_ANSWER = re.compile(
    r"Final Answer:\s*(.+?)(?=\r?\n-{3,}|\r?\nFinal Answer:|\Z)",
    re.IGNORECASE | re.DOTALL,
)
_AGENT_THOUGHTS_FINAL = re.compile(
    r"Final Answer:\s*(.+?)(?:\n-{3,}|\Z)",
    re.IGNORECASE | re.DOTALL,
)


def _looks_like_tool_call_payload(text: str) -> bool:
    """True when NAT printed a native tool-call blob instead of inventory prose."""
    stripped = text.strip()
    if not stripped.startswith("{"):
        return False
    lowered = stripped.casefold()
    return '"name"' in lowered and '"parameters"' in lowered


def _extract_workflow_result_blocks(cleaned: str) -> list[str]:
    """Return text from each ``Workflow Result:`` console block in log order."""
    marker = "Workflow Result:"
    blocks: list[str] = []
    search_from = 0
    while True:
        idx = cleaned.find(marker, search_from)
        if idx == -1:
            break
        tail = cleaned[idx + len(marker) :]
        lines: list[str] = []
        for line in tail.splitlines():
            stripped = line.strip()
            if stripped.startswith("---"):
                break
            if stripped:
                lines.append(stripped)
        blocks.append("\n".join(lines))
        search_from = idx + len(marker)
    return blocks


def _extract_workflow_result_block(cleaned: str) -> str:
    """Return prose from the last non-tool-call ``Workflow Result:`` block."""
    for block in reversed(_extract_workflow_result_blocks(cleaned)):
        if block and not _looks_like_tool_call_payload(block):
            return block
    return ""


def extract_nat_answer_text(raw: str) -> str:
    """Return the best-effort final answer prose from NAT console output."""
    cleaned = _ANSI_ESCAPE.sub("", raw)
    workflow_answer = _extract_workflow_result_block(cleaned)
    if workflow_answer:
        return workflow_answer
    final_answers = list(_FINAL_ANSWER.finditer(cleaned))
    for match in reversed(final_answers):
        answer = match.group(1).strip()
        if answer:
            return answer
    match = _AGENT_THOUGHTS_FINAL.search(cleaned)
    if match:
        answer = match.group(1).strip()
        if answer:
            return answer
    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    if not lines:
        return ""
    return "\n".join(lines[-40:])


def main(argv: list[str] | None = None) -> int:
    """CLI: read nat stdout file, print extracted answer on stdout."""
    parser = argparse.ArgumentParser(description="Extract Final Answer from nat run output.")
    parser.add_argument("input", type=Path, help="Path to captured nat stdout")
    args = parser.parse_args(argv)

    raw = args.input.read_text(encoding="utf-8")
    print(extract_nat_answer_text(raw))
    return 0


if __name__ == "__main__":
    sys.exit(main())
