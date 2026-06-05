"""Offline unit tests for embeddings/rank.py top-k cosine ranking."""

from __future__ import annotations

import math

import pytest

from embeddings.rank import top_k


def test_known_vectors_rank_in_expected_order() -> None:
    """Unit vectors aligned with query rank above orthogonal ones."""
    query = [1.0, 0.0, 0.0]
    half = 1.0 / math.sqrt(2.0)
    matrix = [
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
        [half, half, 0.0],
    ]
    ids = ["exact", "orthogonal", "diagonal"]

    result = top_k(query, matrix, ids, k=3)

    assert [item_id for item_id, _ in result] == ["exact", "diagonal", "orthogonal"]
    assert result[0][1] == pytest.approx(1.0)
    assert result[1][1] == pytest.approx(half)
    assert result[2][1] == pytest.approx(0.0)


def test_top_k_returns_only_k_results() -> None:
    query = [1.0, 0.0]
    matrix = [[1.0, 0.0], [0.0, 1.0], [half := 1.0 / math.sqrt(2.0), half]]
    ids = ["a", "b", "c"]

    result = top_k(query, matrix, ids, k=2)

    assert len(result) == 2
    assert result[0][0] == "a"
    assert result[1][0] == "c"


def test_k_zero_returns_empty_list() -> None:
    query = [1.0, 0.0]
    matrix = [[1.0, 0.0]]
    ids = ["a"]

    assert top_k(query, matrix, ids, k=0) == []


def test_k_negative_returns_empty_list() -> None:
    query = [1.0, 0.0]
    matrix = [[1.0, 0.0]]
    ids = ["a"]

    assert top_k(query, matrix, ids, k=-1) == []


def test_k_larger_than_candidates_returns_all_sorted() -> None:
    query = [1.0, 0.0]
    matrix = [[1.0, 0.0], [0.0, 1.0]]
    ids = ["high", "low"]

    result = top_k(query, matrix, ids, k=10)

    assert len(result) == 2
    assert result[0][0] == "high"
    assert result[1][0] == "low"


def test_ties_preserve_input_order() -> None:
    """Equal scores keep the earlier id first (stable sort)."""
    query = [1.0, 0.0]
    matrix = [
        [1.0, 0.0],
        [1.0, 0.0],
        [0.0, 1.0],
    ]
    ids = ["first", "second", "third"]

    result = top_k(query, matrix, ids, k=3)

    assert [item_id for item_id, _ in result] == ["first", "second", "third"]
    assert result[0][1] == pytest.approx(1.0)
    assert result[1][1] == pytest.approx(1.0)
    assert result[2][1] == pytest.approx(0.0)


def test_empty_matrix_returns_empty_list() -> None:
    assert top_k([1.0, 0.0], [], [], k=5) == []


def test_matrix_ids_length_mismatch_raises() -> None:
    with pytest.raises(ValueError, match="matrix/ids length mismatch"):
        top_k([1.0, 0.0], [[1.0, 0.0]], ["a", "b"], k=1)


def test_row_dimension_mismatch_raises() -> None:
    with pytest.raises(ValueError, match="vector dimension mismatch"):
        top_k([1.0, 0.0], [[1.0, 0.0, 0.0]], ["a"], k=1)


def test_accepts_integer_ids() -> None:
    query = [1.0, 0.0]
    matrix = [[1.0, 0.0], [0.0, 1.0]]
    ids = [101, 202]

    result = top_k(query, matrix, ids, k=1)

    assert result == [(101, pytest.approx(1.0))]
