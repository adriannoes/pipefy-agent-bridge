"""Offline tests for embeddings/card_text.py."""

from __future__ import annotations

import json
import subprocess
from typing import Any

import pytest

from embeddings.card_text import (
    DEFAULT_CARD_TEXT_LIMIT,
    CardText,
    clamp_card_text_limit,
    extract_card_records,
    fetch_card_texts,
    normalize_card_text,
    parse_card_list_json,
)


def _cli_shaped_payload(cards: list[dict[str, Any]]) -> str:
    edges = [{"node": card} for card in cards]
    return json.dumps({"cards": {"edges": edges, "pageInfo": {"hasNextPage": False}}})


def test_normalize_joins_title_and_description_and_collapses_whitespace() -> None:
    assert normalize_card_text("  Late invoice ", "  from vendor X  ") == (
        "Late invoice from vendor X"
    )


def test_normalize_title_only() -> None:
    assert normalize_card_text("Only title", None) == "Only title"
    assert normalize_card_text("Only title", "") == "Only title"


def test_normalize_empty_parts() -> None:
    assert normalize_card_text(None, None) == ""
    assert normalize_card_text("   ", "\n\t") == ""


def test_parse_card_list_json_edges_shape() -> None:
    raw = _cli_shaped_payload(
        [
            {"id": "1", "title": "Alpha", "description": "First"},
            {"id": "2", "title": "Beta", "description": None},
        ]
    )
    cards = parse_card_list_json(raw)
    assert cards == [
        CardText(card_id="1", text="Alpha First", title="Alpha"),
        CardText(card_id="2", text="Beta", title="Beta"),
    ]


def test_parse_card_list_json_bare_cards_list() -> None:
    raw = json.dumps(
        {
            "cards": [
                {"id": "9", "title": "Gamma", "description": "Detail"},
            ]
        }
    )
    cards = parse_card_list_json(raw)
    assert cards == [CardText(card_id="9", text="Gamma Detail", title="Gamma")]


def test_clamp_card_text_limit_enforces_documented_cap() -> None:
    assert clamp_card_text_limit(50) == 50
    assert clamp_card_text_limit(DEFAULT_CARD_TEXT_LIMIT) == DEFAULT_CARD_TEXT_LIMIT
    assert clamp_card_text_limit(500) == DEFAULT_CARD_TEXT_LIMIT
    with pytest.raises(ValueError, match=r">= 1"):
        clamp_card_text_limit(0)


def test_fetch_card_texts_enforces_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = _cli_shaped_payload(
        [{"id": str(i), "title": f"Card {i}", "description": f"Desc {i}"} for i in range(1, 6)]
    )
    captured: dict[str, Any] = {}

    def fake_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        captured["cmd"] = cmd
        captured["kwargs"] = kwargs
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout=payload,
            stderr="",
        )

    monkeypatch.setattr("embeddings.card_text._default_subprocess_runner", fake_run)

    result = fetch_card_texts("306995611", limit=2)
    assert len(result) == 2
    assert result[0].card_id == "1"
    assert result[1].card_id == "2"
    assert captured["cmd"] == [
        "pipefy",
        "card",
        "list",
        "--pipe",
        "306995611",
        "--json",
        "--first",
        "2",
    ]


def test_fetch_card_texts_cli_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=1,
            stdout="",
            stderr="Pipe not found",
        )

    monkeypatch.setattr("embeddings.card_text._default_subprocess_runner", fake_run)

    with pytest.raises(RuntimeError, match=r"pipefy card list failed"):
        fetch_card_texts("bad-pipe", limit=5)


def test_fetch_card_texts_rejects_empty_pipe_id() -> None:
    with pytest.raises(ValueError, match=r"non-empty string"):
        fetch_card_texts("  ", limit=5)


def test_extract_card_records_skips_malformed_edges() -> None:
    payload = {
        "cards": {
            "edges": [
                {"node": {"id": "1", "title": "OK"}},
                {"node": "not-a-dict"},
                "not-an-edge",
            ]
        }
    }
    records = extract_card_records(payload)
    assert len(records) == 1
    assert records[0]["id"] == "1"
