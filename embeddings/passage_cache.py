"""On-disk cache for passage embeddings between ``make similar`` runs."""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from embeddings.card_text import CardText
from embeddings.embed import _resolve_model, _resolve_provider

_MANIFEST_NAME = "manifest.json"
_VECTORS_NAME = "passage_vectors.npy"


@dataclass(frozen=True, slots=True)
class PassageCacheManifest:
    """Read-only cache metadata (no secrets; card ids + titles only)."""

    pipe_id: str
    card_limit: int
    content_fingerprint: str
    embed_provider: str
    embed_model: str
    card_ids: tuple[str, ...]
    titles: tuple[str | None, ...]


def resolve_embed_cache_dir() -> Path | None:
    """Return ``EMBED_CACHE_DIR`` when set, else ``None``."""
    raw = os.environ.get("EMBED_CACHE_DIR", "").strip()
    if not raw:
        return None
    return Path(raw)


def cards_content_fingerprint(cards: Sequence[CardText]) -> str:
    """Stable hash of the embeddable card text set (card_id + text per row).

    Args:
        cards: Cards in fetch order (only those with non-empty text).

    Returns:
        Hex digest used for cache invalidation when text changes.
    """
    digest = hashlib.sha256()
    for card in cards:
        digest.update(card.card_id.encode("utf-8"))
        digest.update(b"\0")
        digest.update(card.text.encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def _cache_entry_dir(
    cache_dir: Path,
    pipe_id: str,
    card_limit: int,
    content_fingerprint: str,
) -> Path:
    key_material = f"{pipe_id}\n{card_limit}\n{content_fingerprint}".encode()
    entry_key = hashlib.sha256(key_material).hexdigest()[:32]
    return cache_dir / entry_key


def _current_embed_identity() -> tuple[str, str]:
    provider = _resolve_provider()
    model = _resolve_model(provider, None)
    return provider, model


def _manifest_to_json(manifest: PassageCacheManifest) -> dict[str, Any]:
    return {
        "pipe_id": manifest.pipe_id,
        "card_limit": manifest.card_limit,
        "content_fingerprint": manifest.content_fingerprint,
        "embed_provider": manifest.embed_provider,
        "embed_model": manifest.embed_model,
        "card_ids": list(manifest.card_ids),
        "titles": list(manifest.titles),
    }


def _manifest_from_json(data: dict[str, Any]) -> PassageCacheManifest:
    card_ids = data.get("card_ids")
    titles = data.get("titles")
    if not isinstance(card_ids, list) or not isinstance(titles, list):
        msg = (
            f"invalid passage cache manifest: card_ids and titles must be lists, "
            f"got card_ids={type(card_ids).__name__}, titles={type(titles).__name__}"
        )
        raise ValueError(msg)
    return PassageCacheManifest(
        pipe_id=str(data["pipe_id"]),
        card_limit=int(data["card_limit"]),
        content_fingerprint=str(data["content_fingerprint"]),
        embed_provider=str(data["embed_provider"]),
        embed_model=str(data["embed_model"]),
        card_ids=tuple(str(card_id) for card_id in card_ids),
        titles=tuple(None if title is None else str(title) for title in titles),
    )


def try_load_passage_vectors(
    cache_dir: Path,
    pipe_id: str,
    card_limit: int,
    cards: list[CardText],
) -> np.ndarray | None:
    """Load cached passage vectors when *pipe_id*, limit, and text set match.

    Args:
        cache_dir: Root directory from ``EMBED_CACHE_DIR``.
        pipe_id: Demo pipe id for this run.
        card_limit: Effective ingestion cap.
        cards: Embeddable cards for this run (non-empty text).

    Returns:
        ``(n, dim)`` float32 matrix on hit, else ``None``.
    """
    fingerprint = cards_content_fingerprint(cards)
    entry_dir = _cache_entry_dir(cache_dir, pipe_id, card_limit, fingerprint)
    manifest_path = entry_dir / _MANIFEST_NAME
    vectors_path = entry_dir / _VECTORS_NAME
    if not manifest_path.is_file() or not vectors_path.is_file():
        return None

    try:
        manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest = _manifest_from_json(manifest_data)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        return None

    provider, model = _current_embed_identity()
    expected_ids = tuple(card.card_id for card in cards)
    if (
        manifest.pipe_id != pipe_id
        or manifest.card_limit != card_limit
        or manifest.content_fingerprint != fingerprint
        or manifest.embed_provider != provider
        or manifest.embed_model != model
        or manifest.card_ids != expected_ids
    ):
        return None

    try:
        vectors = np.load(vectors_path)
    except OSError:
        return None

    if vectors.dtype != np.float32:
        vectors = np.asarray(vectors, dtype=np.float32)
    if vectors.ndim != 2 or vectors.shape[0] != len(cards):
        return None
    return vectors


def write_passage_vectors(
    cache_dir: Path,
    pipe_id: str,
    card_limit: int,
    cards: list[CardText],
    vectors: np.ndarray,
) -> None:
    """Persist passage vectors and metadata (read-only cache; no secrets).

    Args:
        cache_dir: Root directory from ``EMBED_CACHE_DIR``.
        pipe_id: Demo pipe id for this run.
        card_limit: Effective ingestion cap.
        cards: Embeddable cards aligned with *vectors* rows.
        vectors: L2-normalized passage embedding matrix.
    """
    if vectors.shape[0] != len(cards):
        msg = f"vectors row count {vectors.shape[0]!r} does not match cards length {len(cards)!r}"
        raise ValueError(msg)

    fingerprint = cards_content_fingerprint(cards)
    entry_dir = _cache_entry_dir(cache_dir, pipe_id, card_limit, fingerprint)
    entry_dir.mkdir(parents=True, exist_ok=True)

    provider, model = _current_embed_identity()
    manifest = PassageCacheManifest(
        pipe_id=pipe_id,
        card_limit=card_limit,
        content_fingerprint=fingerprint,
        embed_provider=provider,
        embed_model=model,
        card_ids=tuple(card.card_id for card in cards),
        titles=tuple(card.title for card in cards),
    )

    manifest_path = entry_dir / _MANIFEST_NAME
    vectors_path = entry_dir / _VECTORS_NAME
    tmp_manifest = entry_dir / f".{_MANIFEST_NAME}.tmp"
    tmp_vectors = entry_dir / f".{_VECTORS_NAME}.tmp"

    tmp_manifest.write_text(
        json.dumps(_manifest_to_json(manifest), indent=2) + "\n",
        encoding="utf-8",
    )
    with tmp_vectors.open("wb") as vector_file:
        np.save(vector_file, np.asarray(vectors, dtype=np.float32))
    tmp_manifest.replace(manifest_path)
    tmp_vectors.replace(vectors_path)
