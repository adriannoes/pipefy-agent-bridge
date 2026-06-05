"""Pure cosine top-k ranking over L2-normalized embedding vectors."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TypeVar

IdT = TypeVar("IdT")


def _dot(a: Sequence[float], b: Sequence[float]) -> float:
    """Compute the dot product of two equal-length vectors.

    Args:
        a: First vector.
        b: Second vector.

    Returns:
        Sum of element-wise products.

    Raises:
        ValueError: If vector lengths differ.
    """
    if len(a) != len(b):
        msg = (
            f"vector dimension mismatch: query length {len(a)}, "
            f"row length {len(b)}; expected equal lengths"
        )
        raise ValueError(msg)
    return sum(x * y for x, y in zip(a, b, strict=True))


def top_k(
    query_vec: Sequence[float],
    matrix: Sequence[Sequence[float]],
    ids: Sequence[IdT],
    k: int,
) -> list[tuple[IdT, float]]:
    """Return the top-k ids ranked by cosine similarity to the query.

    Vectors are assumed L2-normalized; cosine similarity equals the dot product.

    Ties on score preserve the relative order of ``ids`` (stable sort).

    Args:
        query_vec: Query embedding (length ``d``).
        matrix: Candidate embeddings, shape ``(n, d)``, each row L2-normalized.
        ids: Identifier for each row in ``matrix`` (length ``n``).
        k: Maximum number of results; ``k <= 0`` yields an empty list.

    Returns:
        Up to ``k`` pairs ``(id, score)`` sorted by descending score.

    Raises:
        ValueError: If ``len(matrix) != len(ids)`` or a row length differs from
            ``query_vec``.

    Example:
        >>> top_k([1.0, 0.0], [[1.0, 0.0], [0.0, 1.0]], ["a", "b"], k=1)
        [('a', 1.0)]
    """
    if len(matrix) != len(ids):
        msg = (
            f"matrix/ids length mismatch: matrix has {len(matrix)} rows, "
            f"ids has {len(ids)} entries; expected equal lengths"
        )
        raise ValueError(msg)

    if k <= 0:
        return []

    scored: list[tuple[IdT, float]] = [
        (item_id, _dot(query_vec, row)) for item_id, row in zip(ids, matrix, strict=True)
    ]
    scored.sort(key=lambda pair: pair[1], reverse=True)
    return scored[: min(k, len(scored))]
