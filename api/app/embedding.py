"""Question embedding: the same local BGE model that embedded the passages (ADR 0004)."""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Protocol

from . import modelconfig


class QueryEmbedder(Protocol):
    def embed_query(self, text: str) -> list[float]: ...


class LocalQueryEmbedder:
    def __init__(self, model: Any = None) -> None:
        cfg = modelconfig.model("embeddings")
        if model is None:
            from fastembed import TextEmbedding

            model = TextEmbedding(model_name=cfg["id"])
        self._model = model
        self._prefix: str = cfg.get("query_prefix", "")
        self._dims = int(cfg["dimensions"])

    def embed_query(self, text: str) -> list[float]:
        vec = [float(x) for x in next(iter(self._model.embed([self._prefix + text])))]
        if len(vec) != self._dims:
            raise ValueError(f"expected {self._dims} dims, got {len(vec)}")
        return vec


@lru_cache(maxsize=1)
def get_query_embedder() -> QueryEmbedder:
    return LocalQueryEmbedder()
