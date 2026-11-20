"""Embedders. Titan Text Embeddings V2 (1024 dims) in AWS; a deterministic stub for local/tests."""

from __future__ import annotations

import hashlib
import json
import math
import os
from typing import Any, Protocol

DIMENSIONS = 1024
TITAN_MODEL_ENV = "EMBEDDING_MODEL_ID"  # model IDs come from config, never hard-coded
DEFAULT_TITAN_MODEL = "amazon.titan-embed-text-v2:0"


class Embedder(Protocol):
    def embed(self, text: str) -> list[float]: ...


class StubEmbedder:
    """Deterministic pseudo-embedding from word hashes. No AWS. Similar texts share words, so
    they land closer together, which is enough to exercise search code in tests."""

    def embed(self, text: str) -> list[float]:
        vec = [0.0] * DIMENSIONS
        for word in text.lower().split():
            h = int.from_bytes(hashlib.sha256(word.encode()).digest()[:4], "big")
            vec[h % DIMENSIONS] += 1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]


class TitanEmbedder:
    """Calls Bedrock. Needs AWS credentials (profile sor-dev) and model access."""

    def __init__(self, client: Any = None, model_id: str | None = None) -> None:
        if client is None:
            import boto3

            client = boto3.client("bedrock-runtime", region_name="us-east-2")
        self._client = client
        self._model_id = model_id or os.environ.get(TITAN_MODEL_ENV, DEFAULT_TITAN_MODEL)

    def embed(self, text: str) -> list[float]:
        body = json.dumps({"inputText": text, "dimensions": DIMENSIONS, "normalize": True})
        resp = self._client.invoke_model(modelId=self._model_id, body=body)
        vec: list[float] = json.loads(resp["body"].read())["embedding"]
        if len(vec) != DIMENSIONS:
            raise ValueError(f"expected {DIMENSIONS} dims, got {len(vec)}")
        return vec


def get_embedder(kind: str) -> Embedder:
    if kind == "stub":
        return StubEmbedder()
    if kind == "titan":
        return TitanEmbedder()
    raise ValueError(f"unknown embedder: {kind}")
