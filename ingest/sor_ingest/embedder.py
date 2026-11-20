"""Embedders. A local BGE model (384 dims, no AWS) for real use; a deterministic stub for tests.

No Bedrock embedding model is approved for this account, so embeddings run locally. Model and
dimensions come from config/models.yaml.
"""

from __future__ import annotations

import hashlib
import math
from typing import Any, Protocol

from . import modelconfig

DIMENSIONS: int = int(modelconfig.model("embeddings")["dimensions"])


class Embedder(Protocol):
    def embed(self, text: str) -> list[float]:
        """Embed a passage."""
        ...

    def embed_query(self, text: str) -> list[float]:
        """Embed a search question (BGE wants an instruction prefix on queries only)."""
        ...


class StubEmbedder:
    """Deterministic pseudo-embedding from word hashes. Similar texts share words, so they land
    closer together, which is enough to exercise search code in tests."""

    def embed(self, text: str) -> list[float]:
        vec = [0.0] * DIMENSIONS
        for word in text.lower().split():
            h = int.from_bytes(hashlib.sha256(word.encode()).digest()[:4], "big")
            vec[h % DIMENSIONS] += 1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def embed_query(self, text: str) -> list[float]:
        return self.embed(text)


class LocalEmbedder:
    """BGE small via fastembed (ONNX, CPU). The model is downloaded once and cached."""

    def __init__(self, model: Any = None) -> None:
        cfg = modelconfig.model("embeddings")
        if model is None:
            from fastembed import TextEmbedding

            model = TextEmbedding(model_name=cfg["id"])
        self._model = model
        self._query_prefix: str = cfg.get("query_prefix", "")

    def _one(self, text: str) -> list[float]:
        vec = [float(x) for x in next(iter(self._model.embed([text])))]
        if len(vec) != DIMENSIONS:
            raise ValueError(f"expected {DIMENSIONS} dims, got {len(vec)}")
        return vec

    def embed(self, text: str) -> list[float]:
        return self._one(text)

    def embed_query(self, text: str) -> list[float]:
        return self._one(self._query_prefix + text)


def get_embedder(kind: str) -> Embedder:
    if kind == "stub":
        return StubEmbedder()
    if kind == "local":
        return LocalEmbedder()
    raise ValueError(f"unknown embedder: {kind}")
