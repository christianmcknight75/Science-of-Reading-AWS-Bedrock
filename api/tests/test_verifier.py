from app.schemas import Claim
from app.verifier import normalize, quote_in, verify
from tests.fakes import P1_TEXT, FakeLLM, passage

QUOTE = "Blending means pushing the sounds together smoothly"
RETRIEVED = {"src_0011_p001": passage("src_0011_p001")}


def run(claims: list[Claim], llm: FakeLLM | None = None):  # type: ignore[no-untyped-def]
    return verify(claims, RETRIEVED, llm=llm or FakeLLM(), model_id="m", max_tokens=100)


def test_quote_match_is_exact_apart_from_whitespace_and_typography() -> None:
    assert quote_in(QUOTE, P1_TEXT)
    assert quote_in("Blending  means\npushing the sounds together", P1_TEXT)
    assert not quote_in("blending means pushing the sounds", P1_TEXT)  # case counts
    assert not quote_in("Blending means pushing sounds together", P1_TEXT)  # a word is missing
    assert not quote_in("sounds", P1_TEXT)  # too short to prove anything
    assert normalize("it’s “fine” — ok") == 'it\'s "fine" - ok'


def test_good_claim_is_kept() -> None:
    r = run([Claim("Blend sounds.", ["src_0011_p001"], QUOTE)])
    assert r.ok and len(r.kept) == 1 and r.fabricated_citations == 0 and r.quote_mismatches == 0


def test_cited_id_that_was_not_retrieved_is_fabricated_and_dropped() -> None:
    r = run([Claim("Made up.", ["src_9999_p001"], QUOTE)])
    assert r.fabricated_citations == 1 and not r.kept and not r.ok


def test_fabricated_id_next_to_a_real_one_is_counted_and_removed_from_the_claim() -> None:
    r = run([Claim("Blend.", ["src_0011_p001", "src_9999_p001"], QUOTE)])
    assert r.fabricated_citations == 1
    assert r.kept[0].passage_ids == ["src_0011_p001"]


def test_quote_not_in_cited_passage_removes_claim_without_calling_the_model() -> None:
    llm = FakeLLM()
    r = run([Claim("Blend.", ["src_0011_p001"], "A sentence that is not there at all")], llm)
    assert r.quote_mismatches == 1 and not r.kept and llm.calls == []


def test_unsupported_claim_removed_and_too_little_left_falls_back() -> None:
    claims = [
        Claim("Blend.", ["src_0011_p001"], QUOTE),
        Claim("Other.", ["src_0011_p001"], QUOTE),
        Claim("Third.", ["src_0011_p001"], QUOTE),
    ]
    r = run(claims, FakeLLM(checks=["supported", "unsupported", "unsupported"]))
    assert len(r.kept) == 1 and r.unsupported == 2 and not r.ok  # 1/3 < half


def test_half_kept_is_ok() -> None:
    claims = [Claim("a", ["src_0011_p001"], QUOTE), Claim("b", ["src_0011_p001"], QUOTE)]
    assert run(claims, FakeLLM(checks=["supported", "unsupported"])).ok


def test_contradicted_claim_is_removed_and_its_passage_reported() -> None:
    claims = [Claim("a", ["src_0011_p001"], QUOTE), Claim("b", ["src_0011_p001"], QUOTE)]
    r = run(claims, FakeLLM(checks=["supported", "contradicted"]))
    assert r.contradicted_passage_ids == ["src_0011_p001"]


def test_claim_check_failure_fails_closed() -> None:
    r = run([Claim("a", ["src_0011_p001"], QUOTE)], FakeLLM(fail_check=True))
    assert not r.kept and not r.ok


def test_missing_verdict_fails_closed() -> None:
    claims = [Claim("a", ["src_0011_p001"], QUOTE), Claim("b", ["src_0011_p001"], QUOTE)]
    r = run(claims, FakeLLM(checks=["supported"]))  # no verdict for claim 1
    assert len(r.kept) == 1
