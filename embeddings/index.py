"""Pluggable FAISS vector index: CPU default, GPU opt-in."""

from __future__ import annotations

import os
from dataclasses import dataclass

import numpy as np

DEFAULT_BACKEND = "cpu"


@dataclass(frozen=True, slots=True)
class VectorIndex:
    """Wrapper around a FAISS index built from L2-normalized vectors."""

    backend: str
    dimension: int
    _index: object

    def __len__(self) -> int:
        return int(self._index.ntotal)  # type: ignore[attr-defined]


def build_index(
    vectors: np.ndarray,
    backend: str | None = None,
) -> VectorIndex:
    """Build a flat inner-product index over *vectors* ``(n, dim)``.

      *backend* defaults to ``EMBED_BACKEND`` env (``cpu`` or ``gpu``). Vectors
    should already be L2-normalized (as from ``embed_texts``) so IP == cosine.

      Example:
          >>> import numpy as np
          >>> v = np.eye(3, dtype=np.float32)
          >>> idx = build_index(v, backend="cpu")
          >>> query(idx, v[0], k=1)[0][0]  # doctest: +SKIP
          0
    """
    matrix = _as_float32_matrix(vectors)
    if matrix.ndim != 2:
        raise ValueError(f"vectors must be 2-D, got shape {matrix.shape!r}")
    if matrix.shape[0] == 0:
        raise ValueError("vectors must contain at least one row")

    resolved = _resolve_backend(backend)
    faiss_module = _import_faiss(resolved)
    dimension = int(matrix.shape[1])
    cpu_index = faiss_module.IndexFlatIP(dimension)
    cpu_index.add(matrix)

    if resolved == "cpu":
        return VectorIndex(backend="cpu", dimension=dimension, _index=cpu_index)

    gpu_index = _promote_index_to_gpu(faiss_module, cpu_index)
    return VectorIndex(backend="gpu", dimension=dimension, _index=gpu_index)


def query(index: VectorIndex, vector: np.ndarray, k: int) -> list[tuple[int, float]]:
    """Return up to *k* ``(row_index, score)`` pairs by inner product (cosine if normalized)."""
    if k < 1:
        raise ValueError(f"k must be >= 1, got {k!r}")
    query_vec = _as_float32_matrix(vector)
    if query_vec.ndim == 1:
        query_vec = query_vec.reshape(1, -1)
    if query_vec.shape[1] != index.dimension:
        raise ValueError(
            f"query dimension {query_vec.shape[1]} != index dimension {index.dimension}"
        )

    effective_k = min(k, len(index))
    scores, indices = index._index.search(query_vec, effective_k)  # type: ignore[attr-defined]
    row_scores = scores[0]
    row_indices = indices[0]
    results: list[tuple[int, float]] = []
    for idx, score in zip(row_indices, row_scores, strict=True):
        if idx < 0:
            continue
        results.append((int(idx), float(score)))
    return results


def _resolve_backend(backend: str | None) -> str:
    resolved = (backend or os.environ.get("EMBED_BACKEND", DEFAULT_BACKEND)).strip().lower()
    if resolved not in {"cpu", "gpu"}:
        raise ValueError(
            f"unsupported embed backend {resolved!r}: expected 'cpu' or 'gpu' (EMBED_BACKEND)"
        )
    return resolved


def _as_float32_matrix(vectors: np.ndarray) -> np.ndarray:
    matrix = np.asarray(vectors, dtype=np.float32)
    if not np.isfinite(matrix).all():
        raise ValueError("vectors contain non-finite values")
    return matrix


def _import_faiss(backend: str) -> object:
    try:
        import faiss
    except ImportError as exc:
        raise ImportError(
            "faiss is required for vector indexing: install with `uv sync --extra embeddings` "
            f"(requested backend={backend!r})"
        ) from exc
    return faiss


def _promote_index_to_gpu(faiss_module: object, cpu_index: object) -> object:
    if not hasattr(faiss_module, "StandardGpuResources"):
        raise ImportError(
            "EMBED_BACKEND=gpu requires faiss-gpu (or a FAISS build with GPU support). "
            "Install a GPU-enabled FAISS package, or set EMBED_BACKEND=cpu."
        )
    try:
        resources = faiss_module.StandardGpuResources()  # type: ignore[attr-defined]
        return faiss_module.index_cpu_to_gpu(resources, 0, cpu_index)  # type: ignore[attr-defined]
    except Exception as exc:
        raise RuntimeError(
            "failed to move FAISS index to GPU: install faiss-gpu and ensure a CUDA device "
            "is available, or set EMBED_BACKEND=cpu"
        ) from exc
