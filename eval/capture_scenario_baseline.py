"""Build normalized card baselines for ``stale_cards`` and ``summary`` eval scenarios."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

REPO_ROOT = Path(__file__).resolve().parents[1]
STALE_THRESHOLD_DAYS = 7
STALE_THRESHOLD_SECONDS = STALE_THRESHOLD_DAYS * 86_400
SUMMARY_CARD_LIMIT = 5
CARD_PAGE_SIZE = 100
MAX_CARD_PAGES = 5

_CARDS_QUERY = """
query CardsPage($pipeId: ID!, $first: Int!, $after: String) {
  cards(pipe_id: $pipeId, first: $first, after: $after) {
    edges {
      node {
        id
        title
        done
        createdAt
        current_phase { name }
        current_phase_age
        assignees { name }
      }
    }
    pageInfo { hasNextPage endCursor }
  }
}
""".strip()


class GraphqlRunner(Protocol):
    """Callable that runs a read-only GraphQL document and returns parsed JSON."""

    def __call__(
        self,
        query: str,
        *,
        variables: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...


@dataclass(frozen=True)
class CardRecord:
    """One card row normalized from Pipefy GraphQL."""

    card_id: str
    title: str
    done: bool
    created_at: str | None
    phase_name: str | None
    phase_age_seconds: int | None
    assignee_names: tuple[str, ...]


def _parse_iso_datetime(value: str | None) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _phase_name_matches(actual: str | None, expected: str) -> bool:
    if not actual:
        return False
    return actual.strip().casefold() == expected.strip().casefold()


def _assignee_names_from_node(node: dict[str, Any]) -> tuple[str, ...]:
    assignees = node.get("assignees")
    if not isinstance(assignees, list):
        return ()
    names: list[str] = []
    for assignee in assignees:
        if not isinstance(assignee, dict):
            continue
        name = assignee.get("name")
        if isinstance(name, str) and name.strip():
            names.append(name.strip())
    return tuple(names)


def card_record_from_node(node: dict[str, Any]) -> CardRecord | None:
    """Map one GraphQL card node to :class:`CardRecord`."""
    card_id = node.get("id")
    if not isinstance(card_id, str) or not card_id.strip():
        return None
    title_raw = node.get("title")
    title = "" if title_raw is None else str(title_raw).strip()
    done = bool(node.get("done"))
    created_at = node.get("createdAt")
    created_at_str = created_at if isinstance(created_at, str) else None
    phase_name: str | None = None
    current_phase = node.get("current_phase")
    if isinstance(current_phase, dict):
        phase_raw = current_phase.get("name")
        if isinstance(phase_raw, str) and phase_raw.strip():
            phase_name = phase_raw.strip()
    phase_age = node.get("current_phase_age")
    phase_age_seconds = phase_age if isinstance(phase_age, int) and phase_age >= 0 else None
    return CardRecord(
        card_id=card_id.strip(),
        title=title,
        done=done,
        created_at=created_at_str,
        phase_name=phase_name,
        phase_age_seconds=phase_age_seconds,
        assignee_names=_assignee_names_from_node(node),
    )


def extract_card_nodes(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Return card nodes from a ``cards`` GraphQL page payload."""
    cards = payload.get("cards")
    if not isinstance(cards, dict):
        return []
    edges = cards.get("edges")
    if not isinstance(edges, list):
        return []
    nodes: list[dict[str, Any]] = []
    for edge in edges:
        if not isinstance(edge, dict):
            continue
        node = edge.get("node")
        if isinstance(node, dict):
            nodes.append(node)
    return nodes


def page_info_from_payload(payload: dict[str, Any]) -> tuple[bool, str | None]:
    """Return ``(has_next_page, end_cursor)`` from a cards page."""
    cards = payload.get("cards")
    if not isinstance(cards, dict):
        return False, None
    page_info = cards.get("pageInfo")
    if not isinstance(page_info, dict):
        return False, None
    has_next = page_info.get("hasNextPage") is True
    end_cursor = page_info.get("endCursor")
    cursor = end_cursor if isinstance(end_cursor, str) and end_cursor.strip() else None
    return has_next, cursor


def fetch_pipe_cards(
    pipe_id: str,
    *,
    graphql_runner: GraphqlRunner,
    page_size: int = CARD_PAGE_SIZE,
    max_pages: int = MAX_CARD_PAGES,
) -> list[CardRecord]:
    """Fetch up to ``page_size * max_pages`` cards for *pipe_id* via read-only GraphQL."""
    stripped_pipe = pipe_id.strip()
    if not stripped_pipe:
        msg = f"pipe_id must be a non-empty string, got {pipe_id!r}"
        raise ValueError(msg)

    records: list[CardRecord] = []
    after: str | None = None
    for _ in range(max_pages):
        variables: dict[str, Any] = {
            "pipeId": stripped_pipe,
            "first": page_size,
            "after": after,
        }
        payload = graphql_runner(_CARDS_QUERY, variables=variables)
        for node in extract_card_nodes(payload):
            card = card_record_from_node(node)
            if card is not None:
                records.append(card)
        has_next, after = page_info_from_payload(payload)
        if not has_next or after is None:
            break
    return records


def build_stale_cards_baseline(
    *,
    pipe_id: str,
    phase_name: str,
    cards: list[CardRecord],
    stale_threshold_seconds: int = STALE_THRESHOLD_SECONDS,
) -> dict[str, Any]:
    """Build the normalized ``stale_cards`` baseline document."""
    stale_rows: list[dict[str, str]] = []
    for card in cards:
        if not _phase_name_matches(card.phase_name, phase_name):
            continue
        age = card.phase_age_seconds
        if age is None or age <= stale_threshold_seconds:
            continue
        stale_rows.append({"id": card.card_id, "title": card.title})
    return {
        "scenario": "stale_cards",
        "pipe_id": pipe_id.strip(),
        "phase_name": phase_name.strip(),
        "stale_threshold_days": stale_threshold_seconds // 86_400,
        "stale_cards": stale_rows,
        "stale_count": len(stale_rows),
    }


def build_summary_baseline(
    *,
    pipe_id: str,
    cards: list[CardRecord],
    max_cards: int = SUMMARY_CARD_LIMIT,
) -> dict[str, Any]:
    """Build the normalized ``summary`` baseline (newest open cards)."""
    open_cards = [card for card in cards if not card.done]

    def sort_key(card: CardRecord) -> datetime:
        parsed = _parse_iso_datetime(card.created_at)
        return parsed or datetime.min.replace(tzinfo=UTC)

    ranked = sorted(open_cards, key=sort_key, reverse=True)
    selected = ranked[: max(0, max_cards)]
    rows = [
        {
            "id": card.card_id,
            "title": card.title,
            "phase_name": card.phase_name or "",
            "assignee_names": list(card.assignee_names),
        }
        for card in selected
    ]
    return {
        "scenario": "summary",
        "pipe_id": pipe_id.strip(),
        "max_cards": max_cards,
        "cards": rows,
        "card_count": len(rows),
    }


def default_graphql_runner(
    query: str,
    *,
    variables: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run ``pipefy graphql exec`` and return parsed JSON (read-only)."""
    cmd = [
        "pipefy",
        "graphql",
        "exec",
        "-q",
        query,
        "--json",
    ]
    if variables:
        cmd.extend(["--vars", json.dumps(variables)])
    completed = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=120.0,
        check=False,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip()
        msg = (
            f"pipefy graphql exec failed (exit {completed.returncode})"
            f"{': ' + detail if detail else ''}"
        )
        raise RuntimeError(msg)
    raw = completed.stdout or ""
    if not raw.strip():
        msg = "pipefy graphql exec returned empty JSON"
        raise RuntimeError(msg)
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        msg = f"expected GraphQL JSON object, got {type(payload).__name__!r}"
        raise RuntimeError(msg)
    return payload


def capture_scenario_baseline(
    scenario: str,
    *,
    pipe_id: str,
    phase_name: str | None = None,
    graphql_runner: GraphqlRunner | None = None,
) -> dict[str, Any]:
    """Capture a card baseline for *scenario* using read-only Pipefy GraphQL."""
    normalized = scenario.strip()

    if normalized == "stale_cards":
        if phase_name is None or not phase_name.strip():
            msg = "phase_name is required for stale_cards capture"
            raise ValueError(msg)
    elif normalized != "summary":
        msg = (
            f"unsupported card scenario for capture: {scenario!r} (expected stale_cards or summary)"
        )
        raise ValueError(msg)

    runner = graphql_runner or default_graphql_runner
    cards = fetch_pipe_cards(pipe_id, graphql_runner=runner)

    if normalized == "stale_cards":
        return build_stale_cards_baseline(
            pipe_id=pipe_id,
            phase_name=phase_name,
            cards=cards,
        )
    return build_summary_baseline(pipe_id=pipe_id, cards=cards)


def build_parser() -> argparse.ArgumentParser:
    """CLI argument parser for baseline capture."""
    parser = argparse.ArgumentParser(
        description="Capture stale_cards or summary baseline JSON to stdout.",
    )
    parser.add_argument(
        "scenario",
        choices=("stale_cards", "summary"),
        help="Scenario to capture",
    )
    parser.add_argument(
        "--pipe-id",
        default=None,
        help="Pipe id (default: DEMO_PIPE_ID env)",
    )
    parser.add_argument(
        "--phase-name",
        default=None,
        help="Phase name for stale_cards (default: DEMO_PHASE_NAME env)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry: print normalized baseline JSON."""
    parser = build_parser()
    args = parser.parse_args(argv)

    import os

    pipe_id = (args.pipe_id or os.environ.get("DEMO_PIPE_ID") or "").strip()
    if not pipe_id:
        msg = "missing pipe id: set DEMO_PIPE_ID or pass --pipe-id"
        print(f"error: {msg}", file=sys.stderr)
        return 1

    phase_name = (args.phase_name or os.environ.get("DEMO_PHASE_NAME") or "").strip()
    if args.scenario == "stale_cards" and not phase_name:
        msg = "missing phase name: set DEMO_PHASE_NAME or pass --phase-name"
        print(f"error: {msg}", file=sys.stderr)
        return 1

    try:
        baseline = capture_scenario_baseline(
            args.scenario,
            pipe_id=pipe_id,
            phase_name=phase_name or None,
        )
    except (RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(baseline, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
