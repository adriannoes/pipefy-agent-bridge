"""Offline tests for embeddings/find_similar.py with mocked I/O."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np
import pytest

pytest.importorskip("faiss")

from embeddings.card_text import CardText
from embeddings.find_similar import find_similar


@pytest.fixture
def stub_cards() -> list[CardText]:
    """Three cards with distinct unit-axis embeddings (dim=8)."""
    return [
        CardText(card_id="c-alpha", text="alpha invoice", title="Alpha"),
        CardText(card_id="c-beta", text="beta approval", title="Beta"),
        CardText(card_id="c-gamma", text="gamma vendor", title="Gamma"),
    ]


def test_find_similar_uses_passage_then_query_and_maps_card_ids(
    monkeypatch: pytest.MonkeyPatch,
    stub_cards: list[CardText],
) -> None:
    """Mocked pipeline asserts input_type and returns the best-matching card_id/title."""
    embed_calls: list[dict[str, Any]] = []
    dim = 8

    def fake_fetch(pipe_id: str, limit: int) -> list[CardText]:
        assert pipe_id == "306995611"
        assert limit == 100
        return stub_cards

    def fake_embed(
        texts: Sequence[str],
        *,
        model: str | None = None,
        input_type: str | None = None,
    ) -> np.ndarray:
        embed_calls.append({"texts": list(texts), "input_type": input_type})
        if input_type == "passage":
            rows = []
            for index in range(len(texts)):
                row = np.zeros(dim, dtype=np.float32)
                row[index] = 1.0
                rows.append(row)
            return np.vstack(rows)
        if input_type == "query":
            query_row = np.zeros(dim, dtype=np.float32)
            query_row[1] = 1.0
            return query_row.reshape(1, -1)
        raise AssertionError(f"unexpected input_type={input_type!r}")

    monkeypatch.setattr("embeddings.find_similar.fetch_card_texts", fake_fetch)
    monkeypatch.setattr("embeddings.find_similar.embed_texts", fake_embed)

    hits = find_similar("stale approval", pipe_id="306995611", k=2)

    assert len(embed_calls) == 2
    assert embed_calls[0]["input_type"] == "passage"
    assert embed_calls[0]["texts"] == [card.text for card in stub_cards]
    assert embed_calls[1]["input_type"] == "query"
    assert embed_calls[1]["texts"] == ["stale approval"]

    assert len(hits) == 2
    assert hits[0].card_id == "c-beta"
    assert hits[0].title == "Beta"
    assert hits[0].score == pytest.approx(1.0, abs=1e-5)
    assert hits[1].card_id in {"c-alpha", "c-gamma"}


def test_find_similar_rejects_empty_query() -> None:
    with pytest.raises(ValueError, match=r"non-empty"):
        find_similar("   ", pipe_id="306995611")
