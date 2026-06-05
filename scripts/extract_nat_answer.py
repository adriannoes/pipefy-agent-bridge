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


def _normalize_inventory_text(text: str) -> str:
    """Unescape embedded newlines from Workflow Result JSON strings."""
    return text.replace("\\n", "\n").strip()


def _inventory_answer_score(text: str) -> int:
    """Score inventory prose; more arrow-lines usually means a fuller answer."""
    arrow_lines = sum(1 for line in text.splitlines() if "→" in line or "->" in line)
    return arrow_lines + text.count("→") + text.count("->")


def _looks_like_tool_call_payload(text: str) -> bool:
    """True when NAT printed a native tool-call blob instead of inventory prose."""
    stripped = text.strip()
    lowered = stripped.casefold()
    if "pipefy__" in lowered and '"parameters"' in lowered:
        return True
    if not stripped.startswith("{"):
        return False
    return '"name"' in lowered and '"parameters"' in lowered


def _looks_like_agent_noise(text: str) -> bool:
    """True for Agent's thoughts dumps or instruction echoes, not inventory answers."""
    stripped = text.strip()
    lowered = stripped.casefold()
    if stripped.startswith("Agent's thoughts"):
        return True
    if lowered.startswith("one line per pipe with open card counts"):
        return True
    return _looks_like_tool_call_payload(stripped)


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
        if block and not _looks_like_agent_noise(block):
            return block
    return ""


def _collect_answer_candidates(cleaned: str) -> list[str]:
    """Gather prose blocks that might hold the inventory Final Answer."""
    candidates: list[str] = []
    workflow_answer = _extract_workflow_result_block(cleaned)
    if workflow_answer:
        candidates.append(workflow_answer)
    for match in _FINAL_ANSWER.finditer(cleaned):
        answer = match.group(1).strip()
        if answer and not _looks_like_agent_noise(answer):
            candidates.append(answer)
    return candidates


def _strip_agent_input_blocks(cleaned: str) -> str:
    """Remove echoed user prompts so hint lines are not scored as answers."""
    marker = "Agent input:"
    while marker in cleaned:
        start = cleaned.find(marker)
        end = cleaned.find("\n------------------------------", start)
        if end == -1:
            end = cleaned.find("\nWorkflow Result:", start)
        if end == -1:
            cleaned = cleaned[:start]
            break
        cleaned = cleaned[:start] + cleaned[end:]
    return cleaned


def extract_nat_answer_text(raw: str) -> str:
    """Return the best-effort final answer prose from NAT console output."""
    cleaned = _strip_agent_input_blocks(_ANSI_ESCAPE.sub("", raw))
    candidates = _collect_answer_candidates(cleaned)
    if candidates:
        best_score = max(_inventory_answer_score(candidate) for candidate in candidates)
        tied = [
            candidate
            for candidate in candidates
            if _inventory_answer_score(candidate) == best_score
        ]
        return _normalize_inventory_text(tied[-1])
    final_answers = list(_FINAL_ANSWER.finditer(cleaned))
    for match in reversed(final_answers):
        answer = match.group(1).strip()
        if answer:
            return answer
    match = _AGENT_THOUGHTS_FINAL.search(cleaned)
    if match:
        answer = match.group(1).strip()
        if answer and not _looks_like_agent_noise(answer):
            return _normalize_inventory_text(answer)
    inventory_lines = [
        line.strip()
        for line in cleaned.splitlines()
        if line.strip() and ("→" in line or "->" in line) and not _looks_like_agent_noise(line)
    ]
    if inventory_lines:
        return _normalize_inventory_text("\n".join(inventory_lines[-10:]))
    return ""


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
