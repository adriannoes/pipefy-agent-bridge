"""Batch text embeddings via NIM HTTP API or local sentence-transformers."""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger(__name__)

NIM_EMBEDDINGS_URL = "https://integrate.api.nvidia.com/v1/embeddings"
DEFAULT_PROVIDER = "nim"
DEFAULT_NIM_MODEL = "nvidia/nv-embedqa-e5-v5"
DEFAULT_LOCAL_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_BATCH_SIZE = 32


@dataclass(frozen=True, slots=True)
class ModelConfig:
    """Known embedding model metadata (dimension and NIM input_type behavior)."""

    dim: int
    needs_input_type: bool


MODEL_CONFIGS: dict[str, ModelConfig] = {
    DEFAULT_NIM_MODEL: ModelConfig(dim=1024, needs_input_type=True),
    "nvidia/nv-embed-v1": ModelConfig(dim=4096, needs_input_type=False),
    DEFAULT_LOCAL_MODEL: ModelConfig(dim=384, needs_input_type=False),
}


def embed_texts(
    texts: list[str],
    *,
    model: str | None = None,
    input_type: str | None = None,
) -> np.ndarray:
    """Embed *texts* and return an L2-normalized ``(n, dim)`` float32 matrix.

    Provider and model default from ``EMBED_PROVIDER`` / ``EMBED_MODEL`` (see
    ``embeddings/README.md``). For ``nvidia/nv-embedqa-e5-v5``, pass
    ``input_type='passage'`` when indexing card text and ``input_type='query'``
    for search queries; when omitted, defaults to ``passage``.

    Example:
        >>> vectors = embed_texts(["late invoice"], input_type="query")
        >>> vectors.shape[1]  # doctest: +SKIP
        1024
    """
    if not texts:
        return np.empty((0, _resolve_dim(model)), dtype=np.float32)

    provider = _resolve_provider()
    resolved_model = _resolve_model(provider, model)
    resolved_input_type = _resolve_input_type(resolved_model, input_type)

    if provider == "local":
        raw = _embed_local_batches(texts, resolved_model)
    elif provider == "nim":
        raw = _embed_nim_batches(texts, resolved_model, resolved_input_type)
    else:
        raise ValueError(f"unsupported EMBED_PROVIDER={provider!r}: expected 'nim' or 'local'")

    return _l2_normalize(raw)


def _resolve_provider() -> str:
    return os.environ.get("EMBED_PROVIDER", DEFAULT_PROVIDER).strip().lower() or DEFAULT_PROVIDER


def _resolve_model(provider: str, model: str | None) -> str:
    if model is not None and model.strip():
        return model.strip()
    if provider == "local":
        return os.environ.get("EMBED_MODEL", DEFAULT_LOCAL_MODEL).strip() or DEFAULT_LOCAL_MODEL
    return os.environ.get("EMBED_MODEL", DEFAULT_NIM_MODEL).strip() or DEFAULT_NIM_MODEL


def _resolve_dim(model: str | None) -> int:
    override = os.environ.get("EMBED_DIM", "").strip()
    if override:
        return int(override)
    if model is None:
        model = _resolve_model(_resolve_provider(), None)
    config = MODEL_CONFIGS.get(model)
    if config is not None:
        return config.dim
    raise ValueError(
        f"unknown embedding dimension for model={model!r}: set EMBED_DIM or use a known model "
        f"(known: {sorted(MODEL_CONFIGS)})"
    )


def _resolve_input_type(model: str, input_type: str | None) -> str | None:
    config = MODEL_CONFIGS.get(model)
    if config is None or not config.needs_input_type:
        return None
    if input_type is not None and input_type.strip():
        return input_type.strip()
    return "passage"


def _embed_nim_batches(texts: list[str], model: str, input_type: str | None) -> np.ndarray:
    api_key = os.environ.get("NVIDIA_API_KEY", "").strip()
    if not api_key:
        raise ValueError(
            "NVIDIA_API_KEY is required for EMBED_PROVIDER=nim "
            "(set EMBED_PROVIDER=local for CPU fallback without NIM)"
        )
    batch_size = _batch_size_from_env()
    chunks: list[np.ndarray] = []
    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        chunks.append(
            _nim_embed_http_batch(
                batch,
                model=model,
                input_type=input_type,
                api_key=api_key,
            )
        )
    return np.vstack(chunks).astype(np.float32, copy=False)


def _nim_embed_http_batch(
    texts: list[str],
    *,
    model: str,
    input_type: str | None,
    api_key: str,
) -> np.ndarray:
    """Single NIM embeddings HTTP request (isolated network I/O)."""
    payload: dict[str, object] = {"model": model, "input": texts}
    if input_type is not None:
        payload["input_type"] = input_type

    request = urllib.request.Request(
        NIM_EMBEDDINGS_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"NIM embeddings HTTP {exc.code} for model={model!r}: {detail[:500]}"
        ) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"NIM embeddings request failed for model={model!r}: {exc}") from exc

    data = body.get("data")
    if not isinstance(data, list):
        raise RuntimeError(
            f"NIM embeddings response missing 'data' list: keys={list(body.keys())!r}"
        )
    ordered = sorted(data, key=lambda item: int(item.get("index", 0)))
    vectors = [item["embedding"] for item in ordered]
    if len(vectors) != len(texts):
        raise RuntimeError(
            f"NIM returned {len(vectors)} vectors for {len(texts)} inputs (model={model!r})"
        )
    return np.asarray(vectors, dtype=np.float32)


def _embed_local_batches(texts: list[str], model: str) -> np.ndarray:
    encoder = _load_sentence_transformer(model)
    batch_size = _batch_size_from_env()
    chunks: list[np.ndarray] = []
    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        encoded = encoder.encode(batch, convert_to_numpy=True, show_progress_bar=False)
        chunks.append(np.asarray(encoded, dtype=np.float32))
    return np.vstack(chunks)


def _load_sentence_transformer(model: str) -> object:
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise ImportError(
            "sentence-transformers is required for EMBED_PROVIDER=local: "
            "install with `uv sync --extra embeddings`"
        ) from exc
    logger.debug("loading local embedding model %s", model)
    return SentenceTransformer(model)


def _batch_size_from_env() -> int:
    raw = os.environ.get("EMBED_BATCH_SIZE", "").strip()
    if not raw:
        return DEFAULT_BATCH_SIZE
    size = int(raw)
    if size < 1:
        raise ValueError(f"EMBED_BATCH_SIZE must be >= 1, got {size!r}")
    return size


def _l2_normalize(vectors: np.ndarray) -> np.ndarray:
    """Row-wise L2 normalization so dot product equals cosine similarity."""
    if vectors.size == 0:
        return vectors.astype(np.float32, copy=False)
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1.0, norms)
    return (vectors / norms).astype(np.float32, copy=False)
