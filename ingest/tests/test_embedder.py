import io
import json
from typing import Any

from sor_ingest.embedder import DIMENSIONS, StubEmbedder, TitanEmbedder


def test_stub_is_deterministic_unit_length_1024() -> None:
    e = StubEmbedder()
    a, b = e.embed("sound it out"), e.embed("sound it out")
    assert a == b and len(a) == DIMENSIONS
    assert abs(sum(x * x for x in a) - 1.0) < 1e-9


def test_stub_similar_texts_closer_than_unrelated() -> None:
    e = StubEmbedder()

    def dot(x: list[float], y: list[float]) -> float:
        return sum(i * j for i, j in zip(x, y, strict=True))

    q = e.embed("phonemic awareness blending")
    assert dot(q, e.embed("blending phonemic awareness drills")) > dot(q, e.embed("budget travel"))


class FakeBedrock:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def invoke_model(self, modelId: str, body: str) -> dict[str, Any]:  # noqa: N803
        self.calls.append({"modelId": modelId, "body": json.loads(body)})
        return {"body": io.BytesIO(json.dumps({"embedding": [0.0] * DIMENSIONS}).encode())}


def test_titan_requests_1024_normalized_and_model_from_config(monkeypatch: Any) -> None:
    monkeypatch.setenv("EMBEDDING_MODEL_ID", "test-model")
    fake = FakeBedrock()
    TitanEmbedder(client=fake).embed("hello")
    assert fake.calls[0]["modelId"] == "test-model"
    assert fake.calls[0]["body"]["dimensions"] == 1024 and fake.calls[0]["body"]["normalize"]
