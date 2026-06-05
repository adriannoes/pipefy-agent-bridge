"""Parity: rank.top_k matches FAISS IndexFlatIP on L2-normalized synthetic vectors."""

from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("faiss")

from embeddings.index import build_index, query  # noqa: E402
from embeddings.rank import top_k  # noqa: E402

_SCORE_ATOL = 1e-5
_RNG = np.random.default_rng(42)


def _l2_normalize_rows(matrix: np.ndarray) -> np.ndarray:
    """Return a copy of *matrix* with each row scaled to unit L2 norm."""
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms = np.where(norms == 0.0, 1.0, norms)
    return (matrix / norms).astype(np.float32)


def _assert_top_k_matches_faiss_query(
    vectors: np.ndarray,
    query_vec: np.ndarray,
    k: int,
) -> None:
    """Compare rank.top_k ordering/scores to index.query on the same matrix."""
    matrix_rows = vectors.tolist()
    row_ids = list(range(len(vectors)))
    query_list = query_vec.tolist()

    ranked = top_k(query_list, matrix_rows, row_ids, k=k)
    index = build_index(vectors, backend="cpu")
    faiss_hits = query(index, query_vec, k=k)

    rank_indices = [row_idx for row_idx, _ in ranked]
    rank_scores = [score for _, score in ranked]
    faiss_indices = [row_idx for row_idx, _ in faiss_hits]
    faiss_scores = [score for _, score in faiss_hits]

    assert rank_indices == faiss_indices
    assert rank_scores == pytest.approx(faiss_scores, abs=_SCORE_ATOL)


@pytest.fixture
def normalized_candidate_matrix() -> np.ndarray:
    """Random float32 matrix (n, dim) with L2-normalized rows (distinct scores likely)."""
    raw = _RNG.standard_normal((24, 16), dtype=np.float32)
    return _l2_normalize_rows(raw)


def test_rank_top_k_matches_faiss_for_random_queries(
    normalized_candidate_matrix: np.ndarray,
) -> None:
    """Several query rows and k values agree between rank and FAISS IP search."""
    vectors = normalized_candidate_matrix
    for row in (0, 7, 23):
        query_vec = vectors[row]
        for k in (1, 5, len(vectors)):
            _assert_top_k_matches_faiss_query(vectors, query_vec, k=k)


def test_rank_top_k_matches_faiss_on_orthogonal_unit_vectors() -> None:
    """Unit query along axis 0: unique top-1 hit (ties at score 0 differ in order)."""
    vectors = np.eye(6, dtype=np.float32)
    query_vec = vectors[0]
    _assert_top_k_matches_faiss_query(vectors, query_vec, k=1)


def test_rank_top_k_matches_faiss_off_axis_query(
    normalized_candidate_matrix: np.ndarray,
) -> None:
    """Query not equal to any candidate row still yields matching top-k."""
    vectors = normalized_candidate_matrix
    query_vec = _l2_normalize_rows(_RNG.standard_normal((1, vectors.shape[1]), dtype=np.float32))[0]
    _assert_top_k_matches_faiss_query(vectors, query_vec, k=10)
