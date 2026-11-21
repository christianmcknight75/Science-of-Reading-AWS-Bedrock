from typing import Any

from sor_ingest.embedder import DIMENSIONS, LocalEmbedder, StubEmbedder


def test_stub_is_deterministic_unit_length_from_config() -> None:
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


def test_dimensions_come_from_config() -> None:
    assert DIMENSIONS == 384


class FakeModel:
    def __init__(self) -> None:
        self.inputs: list[str] = []

    def embed(self, texts: list[str]) -> Any:
        self.inputs.extend(texts)
        return iter([[0.0] * DIMENSIONS])


def test_local_embedder_prefixes_queries_only() -> None:
    fake = FakeModel()
    e = LocalEmbedder(model=fake)
    e.embed("a passage")
    e.embed_query("a question")
    assert fake.inputs[0] == "a passage"
    assert fake.inputs[1].startswith("Represent this sentence for searching relevant passages: ")
    assert fake.inputs[1].endswith("a question")
