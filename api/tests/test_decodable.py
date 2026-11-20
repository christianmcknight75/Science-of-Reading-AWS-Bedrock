"""Decodability checker: plain-code rules, no model, no network."""

from __future__ import annotations

import pytest

from app.decodable import DecodabilityChecker, load_heart_words, load_scope, taught_through
from app.decodable.checker import UnknownGrapheme, normalize_taught
from app.decodable.gpc import UNIVERSAL

KINDER = "s a t p i n m d o c k g f l h u b r e j v w x y z qu".split()


def checker(
    *extra: str, taught: list[str] | None = None, hearts: tuple[str, ...] = ()
) -> DecodabilityChecker:
    return DecodabilityChecker((taught or KINDER) + list(extra), hearts)


def ok(c: DecodabilityChecker, word: str) -> list[str]:
    r = c.check(word)
    assert r.status == "decodable" and r.decodable and r.allowed, f"{word}: {r.reason}"
    return r.graphemes


# ---------------------------------------------------------------- simple CVC and blends
@pytest.mark.parametrize("word", ["cat", "sit", "dog", "run", "bed", "hop", "fix", "yes", "jam"])
def test_cvc_words_with_single_letter_sounds(word: str) -> None:
    ok(checker(), word)


@pytest.mark.parametrize(
    ("word", "parts"),
    [
        ("stop", ["s", "t", "o", "p"]),
        ("frog", ["f", "r", "o", "g"]),
        ("plan", ["p", "l", "a", "n"]),
        ("drip", ["d", "r", "i", "p"]),
        ("jump", ["j", "u", "m", "p"]),
        ("crab", ["c", "r", "a", "b"]),
    ],
)
def test_blends_are_just_adjacent_taught_letters(word: str, parts: list[str]) -> None:
    assert ok(checker(), word) == parts


def test_a_word_with_an_untaught_letter_is_not_decodable_and_says_which() -> None:
    c = DecodabilityChecker("s a t".split())
    r = c.check("cat")
    assert r.status == "not_decodable" and not r.decodable and r.needs == ["c"]
    assert "'c'" in r.reason and "not taught" in r.reason


def test_order_in_the_taught_list_does_not_matter() -> None:
    a = DecodabilityChecker(["t", "a", "s"]).check("sat")
    b = DecodabilityChecker(["s", "a", "t"]).check("sat")
    assert a == b and a.decodable


# ---------------------------------------------------------------- digraphs: sh ch th
def test_sh_digraph_needs_to_be_taught() -> None:
    assert ok(checker("sh"), "ship") == ["sh", "i", "p"]
    assert ok(checker("sh"), "fish") == ["f", "i", "sh"]
    r = checker().check("ship")  # s + h + i + p does NOT make /sh/
    assert not r.decodable and r.needs == ["sh"]


def test_ch_digraph() -> None:
    assert ok(checker("ch"), "chop") == ["ch", "o", "p"]
    assert ok(checker("ch"), "much") == ["m", "u", "ch"]
    assert checker().check("chip").needs == ["ch"]


def test_th_digraph_covers_both_sounds() -> None:
    c = checker("th")
    assert ok(c, "thin") == ["th", "i", "n"]  # /th/
    assert ok(c, "this") == ["th", "i", "s"]  # /th/ voiced
    assert ok(c, "that") == ["th", "a", "t"]
    assert checker().check("thin").needs == ["th"]


def test_ck_ng_nk_wh_digraphs() -> None:
    assert ok(checker("ck"), "duck") == ["d", "u", "ck"]
    assert ok(checker("ng"), "sing") == ["s", "i", "ng"]
    assert ok(checker("nk"), "bank") == ["b", "a", "nk"]
    assert ok(checker("nk", "th"), "think") == ["th", "i", "nk"]
    assert ok(checker("wh"), "when") == ["wh", "e", "n"]
    assert not checker().check("duck").decodable


def test_the_digraph_letters_alone_do_not_unlock_the_digraph_in_other_words() -> None:
    # "sh" taught: "sun" must not be read s+u+n differently, and "ash" works
    c = checker("sh")
    assert ok(c, "sun") == ["s", "u", "n"] and ok(c, "ash") == ["a", "sh"]


# ---------------------------------------------------------------- silent e (split digraphs)
def test_silent_e_pattern() -> None:
    c = checker("a_e", "i_e", "o_e", "u_e")
    assert ok(c, "make") == ["m", "a_e", "k"]
    assert ok(c, "bike") == ["b", "i_e", "k"]
    assert ok(c, "hope") == ["h", "o_e", "p"]
    assert ok(c, "cube") == ["c", "u_e", "b"]
    assert ok(c, "gave") == ["g", "a_e", "v"]


def test_silent_e_with_a_digraph_in_the_middle() -> None:
    c = checker("a_e", "sh", "ch", "th")
    assert ok(c, "shake") == ["sh", "a_e", "k"]
    assert ok(c, "bathe") == ["b", "a_e", "th"]


def test_silent_e_not_taught_means_not_decodable() -> None:
    r = checker().check("make")
    assert not r.decodable and r.needs == ["a_e"] and "long a" in r.reason


def test_short_and_long_vowel_words_both_work_when_both_are_taught() -> None:
    c = checker("a_e")
    assert ok(c, "mat") == ["m", "a", "t"] and ok(c, "mate") == ["m", "a_e", "t"]


def test_final_e_is_not_silent_just_because_it_is_final() -> None:
    # "the": no silent-e pattern applies; e says /eh/ here, which does not match
    r = checker("th").check("the")
    assert not r.decodable


def test_split_digraph_cannot_jump_over_a_vowel() -> None:
    # "area"-style spellings: a_e needs consonants between the vowel and the final e
    assert ok(checker("a_e"), "tale") == ["t", "a_e", "l"]
    assert not checker("a_e").check("idea").decodable


# ---------------------------------------------------------------- doubles, plurals, x, qu
def test_floss_doubles_count_as_the_single_consonant() -> None:
    assert ok(checker(), "bell") == ["b", "e", "ll"]
    assert ok(checker(), "miss") == ["m", "i", "ss"]
    assert ok(checker(), "off") == ["o", "ff"]
    assert ok(checker(), "buzz") == ["b", "u", "zz"]
    assert DecodabilityChecker(["b", "e", "ll"]).check("bell").decodable  # "ll" token accepted


def test_final_s_may_say_z() -> None:
    assert ok(checker(), "dogs") == ["d", "o", "g", "s"]
    assert ok(checker(), "his") == ["h", "i", "s"]
    assert not checker().check("is").decodable  # too short: taught as a heart word instead


def test_x_and_qu_are_two_sounds_each() -> None:
    assert ok(checker(), "fox") == ["f", "o", "x"]
    assert ok(checker("ee"), "queen") == ["qu", "ee", "n"]
    assert not DecodabilityChecker("f o s".split()).check("fox").decodable


def test_vowel_teams_and_r_controlled() -> None:
    assert ok(checker("ee"), "tree") == ["t", "r", "ee"]
    assert ok(checker("ai"), "rain") == ["r", "ai", "n"]
    assert ok(checker("oa"), "boat") == ["b", "oa", "t"]
    assert ok(checker("ar"), "car") == ["c", "ar"]
    assert ok(checker("or"), "for") == ["f", "or"]
    assert checker().check("rain").needs == ["ai"]


# ---------------------------------------------------------------- heart words, unknowns
def test_heart_word_is_allowed_but_never_called_decodable() -> None:
    c = checker(hearts=("the", "said"))
    r = c.check("the")
    assert r.status == "heart_word" and r.allowed and not r.decodable
    assert c.check("said").status == "heart_word"
    assert checker().check("said").status == "not_decodable"  # not on the list: not allowed


def test_a_heart_word_that_is_also_decodable_counts_as_decodable() -> None:
    r = checker(hearts=("and",)).check("and")
    assert r.status == "decodable" and r.decodable


def test_irregular_spellings_are_explained() -> None:
    r = checker().check("was")
    assert r.status == "not_decodable" and "heart word" in r.reason


def test_unknown_words_and_symbols_are_not_allowed() -> None:
    c = checker(hearts=("can't",))
    for w in ("blorp", "", "c4t", "x-ray"):
        r = c.check(w)
        assert r.status == "unknown" and not r.allowed and not r.decodable
    assert c.check("can't").status == "heart_word"  # explicit list wins over the symbol rule
    assert checker().check("don't").status == "unknown"


def test_case_and_whitespace_are_ignored_but_the_word_is_returned_as_given() -> None:
    r = checker().check("  Cat ")
    assert r.decodable and r.word == "  Cat "


def test_multiple_pronunciations_any_match_counts() -> None:
    c = DecodabilityChecker(
        ["d", "o", "g"], pronunciations={"dog": [["D", "AO", "G"], ["D", "AA", "G"]]}
    )
    assert c.check("dog").decodable


# ---------------------------------------------------------------- inputs and seed data
def test_unknown_grapheme_names_are_rejected_not_ignored() -> None:
    with pytest.raises(UnknownGrapheme) as e:
        DecodabilityChecker(["s", "zh", "q"])
    assert e.value.names == ["zh", "q"]


def test_taught_names_are_normalized() -> None:
    assert normalize_taught([" S ", "SH", "a_E", "s"]) == ["s", "sh", "a_e"]


def test_check_text_keeps_order_and_length() -> None:
    out = checker().check_text(["a", "cat", "sat"])
    assert [r.word for r in out] == ["a", "cat", "sat"]
    assert [r.status for r in out] == ["not_decodable", "decodable", "decodable"]


def test_scope_and_sequence_seed_is_valid_and_ordered() -> None:
    scope = load_scope()
    assert [r["position"] for r in scope] == list(range(1, len(scope) + 1))
    for r in scope:
        base = r["grapheme"]
        base = base[0] if len(base) == 2 and base[0] == base[1] else base
        assert base in UNIVERSAL, base
    first_ten = taught_through(scope, 10)
    assert first_ten[:3] == ["s", "a", "t"] and len(first_ten) == 10
    c = DecodabilityChecker(first_ten)
    assert c.check("sat").decodable and not c.check("bug").decodable  # b, u come later


def test_heart_word_seed_is_a_plain_lowercase_list() -> None:
    words = load_heart_words()
    assert "the" in words and all(w == w.lower() and w.strip() for w in words)


def test_final_e_without_the_pattern_and_consonant_plus_e_endings() -> None:
    r = checker().check("bake")  # a and e are taught, but not the silent-e pattern
    assert not r.decodable and r.needs == ["a_e"]
    r = checker().check("have")
    assert not r.decodable and r.needs == ["ve"]
    assert ok(checker("ve"), "have") == ["h", "a", "ve"]


def test_every_taught_grapheme_in_the_table_is_usable() -> None:
    for g in UNIVERSAL:
        assert DecodabilityChecker([g]).taught == {g}
