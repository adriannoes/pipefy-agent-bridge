"""Bounded card text ingestion from the ``pipefy`` CLI."""

from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

# Documented cap for semantic search over a demo pipe (see embeddings/README.md).
DEFAULT_CARD_TEXT_LIMIT = 100

SubprocessRunner = Callable[..., subprocess.CompletedProcess[str]]


@dataclass(frozen=True, slots=True)
class CardText:
    """Normalized card text for embedding."""

    card_id: str
    text: str
    title: str | None = None


def clamp_card_text_limit(limit: int) -> int:
    """Return a positive limit bounded by :data:`DEFAULT_CARD_TEXT_LIMIT`.

    Args:
        limit: Requested maximum number of cards.

    Returns:
        ``limit`` when ``1 <= limit <= DEFAULT_CARD_TEXT_LIMIT``.

    Raises:
        ValueError: When *limit* is not a positive integer.
    """
    if limit < 1:
        msg = f"limit must be >= 1, got {limit!r}"
        raise ValueError(msg)
    if limit > DEFAULT_CARD_TEXT_LIMIT:
        return DEFAULT_CARD_TEXT_LIMIT
    return limit


def normalize_card_text(
    title: str | None,
    description: str | None,
) -> str:
    """Join title and description into a single searchable string.

    Whitespace within and between parts is collapsed to single spaces.

    Args:
        title: Card title from CLI JSON (may be empty).
        description: Card description from CLI JSON (may be empty).

    Returns:
        Normalized text, or an empty string when both inputs are empty.

    Example:
        >>> normalize_card_text("  Late invoice ", "  from vendor X  ")
        'Late invoice from vendor X'
    """
    parts: list[str] = []
    for value in (title, description):
        if value is None:
            continue
        stripped = str(value).strip()
        if stripped:
            parts.append(stripped)
    if not parts:
        return ""
    combined = " ".join(parts)
    return re.sub(r"\s+", " ", combined).strip()


def _card_id_from_record(record: Mapping[str, Any]) -> str | None:
    raw = record.get("id", record.get("card_id"))
    if raw is None:
        return None
    card_id = str(raw).strip()
    return card_id or None


def _description_from_record(record: Mapping[str, Any]) -> str | None:
    if "description" in record:
        raw = record.get("description")
        return None if raw is None else str(raw)
    fields = record.get("fields")
    if not isinstance(fields, list):
        return None
    for field in fields:
        if not isinstance(field, dict):
            continue
        name = str(field.get("name") or "").strip().lower()
        if name == "description":
            value = field.get("value")
            return None if value is None else str(value)
    return None


def card_record_to_card_text(record: Mapping[str, Any]) -> CardText | None:
    """Map one CLI card object to :class:`CardText`.

    Args:
        record: Card dict from ``pipefy card list --json`` (node or flat card).

    Returns:
        ``CardText`` when ``id``/``card_id`` is present; otherwise ``None``.
    """
    card_id = _card_id_from_record(record)
    if card_id is None:
        return None
    title_raw = record.get("title")
    title = None if title_raw is None else str(title_raw)
    description = _description_from_record(record)
    text = normalize_card_text(title, description)
    title_stored = title.strip() if title and title.strip() else None
    return CardText(card_id=card_id, text=text, title=title_stored)


def extract_card_records(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Extract card dicts from ``pipefy card list --json`` output.

    Supports GraphQL relay shape (``cards.edges[].node``) and a bare ``cards`` list.

    Args:
        payload: Parsed JSON object from the CLI.

    Returns:
        Card dicts in CLI order.
    """
    cards_section = payload.get("cards")
    if isinstance(cards_section, list):
        return [item for item in cards_section if isinstance(item, dict)]

    if not isinstance(cards_section, dict):
        return []

    edges = cards_section.get("edges")
    if not isinstance(edges, list):
        return []

    records: list[dict[str, Any]] = []
    for edge in edges:
        if not isinstance(edge, dict):
            continue
        node = edge.get("node")
        if isinstance(node, dict):
            records.append(node)
    return records


def parse_card_list_json(raw: str) -> list[CardText]:
    """Parse CLI stdout JSON into normalized card texts (no subprocess).

    Args:
        raw: UTF-8 JSON string from ``pipefy card list --pipe … --json``.

    Returns:
        One :class:`CardText` per card with an id, preserving CLI order.

    Raises:
        ValueError: When JSON is empty or not an object.
        json.JSONDecodeError: When JSON is invalid.
    """
    if not raw.strip():
        msg = "card list JSON is empty"
        raise ValueError(msg)
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        msg = f"expected JSON object from card list, got {type(payload).__name__!r}"
        raise ValueError(msg)
    records = extract_card_records(payload)
    out: list[CardText] = []
    for record in records:
        card = card_record_to_card_text(record)
        if card is not None:
            out.append(card)
    return out


def _default_subprocess_runner(
    cmd: Sequence[str],
    *,
    timeout_s: float | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(cmd),
        capture_output=True,
        text=True,
        timeout=timeout_s,
        check=False,
    )


def _build_card_list_command(pipe_id: str, *, cli_first: int) -> list[str]:
    return [
        "pipefy",
        "card",
        "list",
        "--pipe",
        pipe_id,
        "--json",
        "--first",
        str(cli_first),
    ]


def fetch_card_texts(
    pipe_id: str,
    limit: int = DEFAULT_CARD_TEXT_LIMIT,
    *,
    subprocess_runner: SubprocessRunner | None = None,
    timeout_s: float = 120.0,
) -> list[CardText]:
    """Fetch bounded card texts for a pipe via the ``pipefy`` CLI (read-only).

    Invokes ``pipefy card list --pipe <pipe_id> --json --first <n>`` and normalizes
    each card's title and description into a single ``text`` field.

    Args:
        pipe_id: Demo pipe id (numeric string).
        limit: Maximum cards to return (capped at :data:`DEFAULT_CARD_TEXT_LIMIT`).
        subprocess_runner: Injectable runner for tests (defaults to :func:`subprocess.run`).
        timeout_s: Subprocess timeout in seconds.

    Returns:
        At most *limit* :class:`CardText` records.

    Raises:
        ValueError: When *pipe_id* is empty or *limit* is invalid.
        RuntimeError: When the CLI fails or returns invalid JSON.
    """
    stripped_pipe = pipe_id.strip()
    if not stripped_pipe:
        msg = f"pipe_id must be a non-empty string, got {pipe_id!r}"
        raise ValueError(msg)

    effective_limit = clamp_card_text_limit(limit)
    cmd = _build_card_list_command(stripped_pipe, cli_first=effective_limit)
    run = subprocess_runner or _default_subprocess_runner
    completed = run(cmd, timeout_s=timeout_s)

    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip()
        msg = (
            f"pipefy card list failed for pipe_id={stripped_pipe!r} "
            f"(exit {completed.returncode})"
            f"{': ' + detail if detail else ''}"
        )
        raise RuntimeError(msg)

    stdout = completed.stdout or ""
    try:
        cards = parse_card_list_json(stdout)
    except json.JSONDecodeError as exc:
        msg = f"invalid JSON from pipefy card list for pipe_id={stripped_pipe!r}: {exc}"
        raise RuntimeError(msg) from exc
    except ValueError as exc:
        msg = f"invalid card list payload for pipe_id={stripped_pipe!r}: {exc}"
        raise RuntimeError(msg) from exc

    return cards[:effective_limit]
