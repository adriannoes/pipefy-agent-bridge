"""Offline tests for embeddings/index.py (synthetic vectors, no network)."""

from __future__ import annotations

import numpy as np
import pytest

faiss = pytest.importorskip("faiss")

from embeddings.index import build_index, query  # noqa: E402


def test_build_index_query_returns_nearest_neighbor() -> None:
    """Orthogonal unit vectors: query along axis 0 ranks index 0 first."""
    vectors = np.eye(4, dtype=np.float32)
    index = build_index(vectors, backend="cpu")
    hits = query(index, vectors[0], k=2)
    assert hits[0] == (0, pytest.approx(1.0, abs=1e-5))
    assert hits[1][0] != 0


def test_query_k_bounds_to_index_size() -> None:
    vectors = np.eye(2, dtype=np.float32)
    index = build_index(vectors, backend="cpu")
    hits = query(index, vectors[1], k=10)
    assert len(hits) == 2
