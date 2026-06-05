"""Offline tests for embeddings/embed.py (no network)."""

from __future__ import annotations

import numpy as np

from embeddings.embed import embed_texts


def test_embed_texts_empty_returns_zero_by_dim() -> None:
    result = embed_texts([])
    assert result.shape == (0, 1024)
    assert result.dtype == np.float32
