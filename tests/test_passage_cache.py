"""Offline tests for embeddings/passage_cache.py."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from embeddings.card_text import CardText
from embeddings.passage_cache import (
    cards_content_fingerprint,
    try_load_passage_vectors,
    write_passage_vectors,
)


@pytest.fixture
def stub_cards() -> list[CardText]:
    return [
        CardText(card_id="c-alpha", text="alpha invoice", title="Alpha"),
        CardText(card_id="c-beta", text="beta approval", title="Beta"),
    ]


def test_cards_content_fingerprint_changes_when_text_changes(
    stub_cards: list[CardText],
) -> None:
    base = cards_content_fingerprint(stub_cards)
    altered = [
        CardText(card_id="c-alpha", text="alpha invoice CHANGED", title="Alpha"),
        stub_cards[1],
    ]
    assert cards_content_fingerprint(altered) != base


def test_find_similar_cache_miss_then_hit_skips_passage_embed(
    monkeypatch: pytest.MonkeyPatch,
    stub_cards: list[CardText],
    tmp_path: Path,
) -> None:
    """First run embeds passages and writes cache; second run embeds query only."""
    pytest.importorskip("faiss")

    from embeddings.find_similar import find_similar

    cache_dir = tmp_path / "embed-cache"
    monkeypatch.setenv("EMBED_CACHE_DIR", str(cache_dir))

    embed_calls: list[dict[str, Any]] = []
    dim = 8

    def fake_fetch(pipe_id: str, limit: int) -> list[CardText]:
        assert pipe_id == "pipe-1"
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

    find_similar("stale approval", pipe_id="pipe-1", k=1)
    assert len(embed_calls) == 2
    assert embed_calls[0]["input_type"] == "passage"

    embed_calls.clear()
    find_similar("stale approval", pipe_id="pipe-1", k=1)
    assert len(embed_calls) == 1
    assert embed_calls[0]["input_type"] == "query"


def test_try_load_returns_none_when_fingerprint_differs(
    stub_cards: list[CardText],
    tmp_path: Path,
) -> None:
    cache_dir = tmp_path / "cache"
    vectors = np.eye(2, dtype=np.float32)
    write_passage_vectors(cache_dir, "pipe-1", 100, stub_cards, vectors)

    altered = [
        CardText(card_id="c-alpha", text="different text", title="Alpha"),
        stub_cards[1],
    ]
    assert try_load_passage_vectors(cache_dir, "pipe-1", 100, altered) is None
