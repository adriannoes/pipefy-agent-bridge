"""Operator entrypoint: semantic top-k similar cards in the demo pipe."""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass

import numpy as np

from embeddings.card_text import (
    DEFAULT_CARD_TEXT_LIMIT,
    CardText,
    clamp_card_text_limit,
    fetch_card_texts,
)
from embeddings.embed import embed_texts
from embeddings.index import build_index, query
from embeddings.passage_cache import (
    resolve_embed_cache_dir,
    try_load_passage_vectors,
    write_passage_vectors,
)

# Bounded ingestion cap (FR-6): at most DEFAULT_CARD_TEXT_LIMIT cards from DEMO_PIPE_ID.
_DEFAULT_K = 5


@dataclass(frozen=True, slots=True)
class SimilarCard:
    """One ranked search hit for operator output."""

    card_id: str
    score: float
    title: str | None = None


def _resolve_demo_pipe_id() -> str:
    pipe_id = os.environ.get("DEMO_PIPE_ID", "").strip()
    if not pipe_id:
        msg = (
            "DEMO_PIPE_ID is required (set in .env); "
            "semantic search runs only over the configured demo pipe"
        )
        raise ValueError(msg)
    return pipe_id


def _cards_with_text(cards: list[CardText]) -> list[CardText]:
    return [card for card in cards if card.text.strip()]


def _embed_passage_vectors(
    cards: list[CardText],
    *,
    pipe_id: str,
    card_limit: int,
) -> np.ndarray:
    """Embed card passages, using ``EMBED_CACHE_DIR`` when configured."""
    cache_dir = resolve_embed_cache_dir()
    if cache_dir is not None:
        cached = try_load_passage_vectors(cache_dir, pipe_id, card_limit, cards)
        if cached is not None:
            return cached

    vectors = embed_texts([card.text for card in cards], input_type="passage")
    if cache_dir is not None:
        write_passage_vectors(cache_dir, pipe_id, card_limit, cards, vectors)
    return vectors


def find_similar(
    query_text: str,
    *,
    pipe_id: str,
    k: int = _DEFAULT_K,
    card_limit: int = DEFAULT_CARD_TEXT_LIMIT,
    backend: str | None = None,
) -> list[SimilarCard]:
    """Return top-k cards in *pipe_id* most similar to *query_text*.

    Pipeline: ``fetch_card_texts`` → embed passages → ``build_index`` →
    embed query (``input_type=query`` for e5-v5) → FAISS ``query``.

    Card count is capped at :data:`~embeddings.card_text.DEFAULT_CARD_TEXT_LIMIT`
    (100) per ``card_limit`` / env ``CARD_TEXT_LIMIT``.

    Args:
        query_text: Natural-language search string.
        pipe_id: Demo pipe id (typically ``DEMO_PIPE_ID``).
        k: Maximum hits to return.
        card_limit: Upper bound on cards fetched from Pipefy (clamped to 100).
        backend: ``cpu`` or ``gpu``; defaults to ``EMBED_BACKEND`` env.

    Returns:
        Hits sorted by descending similarity score.

    Raises:
        ValueError: When *query_text* or *pipe_id* is empty, or no embeddable cards.
    """
    stripped_query = query_text.strip()
    if not stripped_query:
        raise ValueError(f"query_text must be non-empty, got {query_text!r}")

    effective_k = max(1, k)
    effective_limit = clamp_card_text_limit(card_limit)

    cards = _cards_with_text(fetch_card_texts(pipe_id.strip(), effective_limit))
    if not cards:
        raise ValueError(
            f"no cards with non-empty text in pipe_id={pipe_id!r} "
            f"(limit={effective_limit}); cannot build index"
        )

    passage_vectors = _embed_passage_vectors(
        cards,
        pipe_id=pipe_id.strip(),
        card_limit=effective_limit,
    )
    index = build_index(passage_vectors, backend=backend)

    query_matrix = embed_texts([stripped_query], input_type="query")
    query_vec = np.asarray(query_matrix[0], dtype=np.float32)

    row_hits = query(index, query_vec, effective_k)
    return [
        SimilarCard(
            card_id=cards[row_index].card_id,
            title=cards[row_index].title,
            score=score,
        )
        for row_index, score in row_hits
    ]


def format_similar_line(hit: SimilarCard) -> str:
    """Format one hit for stdout (operator-readable)."""
    title_part = f" title={hit.title!r}" if hit.title else ""
    return f"card_id={hit.card_id}{title_part} score={hit.score:.4f}"


def print_similar_results(results: list[SimilarCard]) -> None:
    """Print top-k lines to stdout."""
    if not results:
        print("(no similar cards)")
        return
    for hit in results:
        print(format_similar_line(hit))


def _card_limit_from_env() -> int:
    raw = os.environ.get("CARD_TEXT_LIMIT", "").strip()
    if not raw:
        return DEFAULT_CARD_TEXT_LIMIT
    return clamp_card_text_limit(int(raw))


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for ``make similar`` and ``python -m embeddings.find_similar``."""
    parser = argparse.ArgumentParser(
        description="Find semantically similar cards in DEMO_PIPE_ID (read-only).",
    )
    parser.add_argument(
        "--query",
        required=True,
        help="Natural-language query (Makefile passes QUERY=...).",
    )
    parser.add_argument(
        "--k",
        type=int,
        default=_DEFAULT_K,
        help=f"Number of results (default: {_DEFAULT_K}).",
    )
    parser.add_argument(
        "--pipe-id",
        default=None,
        help="Override pipe id (default: DEMO_PIPE_ID from environment).",
    )
    args = parser.parse_args(argv)

    try:
        pipe_id = (args.pipe_id or _resolve_demo_pipe_id()).strip()
        if not pipe_id:
            raise ValueError("pipe_id must be non-empty")
        results = find_similar(
            args.query,
            pipe_id=pipe_id,
            k=args.k,
            card_limit=_card_limit_from_env(),
        )
    except (ValueError, ImportError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print_similar_results(results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
