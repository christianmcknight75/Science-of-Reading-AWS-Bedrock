"""Grapheme-phoneme correspondences (GPCs) for the decodability checker.

Phonemes are CMU Pronouncing Dictionary (ARPAbet) symbols without stress digits.
`UNIVERSAL` lists the correspondences we know about, each flagged by whether it is a vowel
grapheme. A teacher "teaches" a subset of these by name ("sh", "a_e", "ee" ...). The checker may
only use taught ones; the rest are used only to explain what a failing word still needs.

Rules worth knowing (all deliberate, all tested):
- A short vowel letter has one sound: a=/ae/, e=/eh/, i=/ih/, o=/aa/ or /ao/, u=/uh/.
- A doubled consonant counts as the taught single consonant (hill = h-i-ll uses "l").
- Final "s" may say /z/ ("dogs", "his") when the word has at least 3 letters.
- A split digraph ("a_e") is a vowel, one consonant grapheme, then a final silent "e".
- "c" says /k/ and "g" says /g/ only (soft c and g are not taught by default).
"""

from __future__ import annotations

from dataclasses import dataclass

Reading = tuple[str, ...]  # a sequence of phonemes, e.g. ("K", "S") for "x"


@dataclass(frozen=True)
class Gpc:
    grapheme: str  # "sh", "a_e" (split digraph), "ee"
    readings: tuple[Reading, ...]
    vowel: bool

    @property
    def split(self) -> bool:
        return "_" in self.grapheme

    @property
    def orth(self) -> str:
        """Letters as they appear in the word (for a split digraph, only the first letter)."""
        return self.grapheme.split("_")[0]


def _g(grapheme: str, *readings: str, vowel: bool = False) -> Gpc:
    return Gpc(grapheme, tuple(tuple(r.split()) for r in readings), vowel)


_LIST: list[Gpc] = [
    # single consonants (c and g are hard only; s may also say /z/ at the end of a word)
    _g("b", "B"),
    _g("c", "K"),
    _g("d", "D"),
    _g("f", "F"),
    _g("g", "G"),
    _g("h", "HH"),
    _g("j", "JH"),
    _g("k", "K"),
    _g("l", "L"),
    _g("m", "M"),
    _g("n", "N"),
    _g("p", "P"),
    _g("qu", "K W"),
    _g("r", "R"),
    _g("s", "S"),
    _g("t", "T"),
    _g("v", "V"),
    _g("w", "W"),
    _g("x", "K S"),
    _g("y", "Y"),
    _g("z", "Z"),
    # consonant digraphs and others
    _g("sh", "SH"),
    _g("ch", "CH"),
    _g("th", "TH", "DH"),
    _g("ck", "K"),
    _g("ng", "NG"),
    _g("nk", "NG K"),
    _g("wh", "W"),
    _g("ph", "F"),
    _g("kn", "N"),
    _g("wr", "R"),
    _g("tch", "CH"),
    _g("dge", "JH"),
    # short vowels
    _g("a", "AE", vowel=True),
    _g("e", "EH", vowel=True),
    _g("i", "IH", vowel=True),
    _g("o", "AA", "AO", vowel=True),
    _g("u", "AH", vowel=True),
    # split digraphs (silent e)
    _g("a_e", "EY", vowel=True),
    _g("e_e", "IY", vowel=True),
    _g("i_e", "AY", vowel=True),
    _g("o_e", "OW", vowel=True),
    _g("u_e", "UW", "Y UW", vowel=True),
    # vowel teams
    _g("ee", "IY", vowel=True),
    _g("ea", "IY", "EH", vowel=True),
    _g("ai", "EY", vowel=True),
    _g("ay", "EY", vowel=True),
    _g("oa", "OW", vowel=True),
    _g("ow", "OW", "AW", vowel=True),
    _g("ou", "AW", vowel=True),
    _g("oi", "OY", vowel=True),
    _g("oy", "OY", vowel=True),
    _g("oo", "UW", "UH", vowel=True),
    _g("aw", "AO", "AA", vowel=True),
    _g("au", "AO", "AA", vowel=True),
    _g("ew", "UW", vowel=True),
    _g("igh", "AY", vowel=True),
    _g("ie", "IY", "AY", vowel=True),
    # r-controlled vowels
    _g("ar", "AA R", vowel=True),
    _g("or", "AO R", vowel=True),
    _g("er", "ER", vowel=True),
    _g("ir", "ER", vowel=True),
    _g("ur", "ER", vowel=True),
    # consonant + silent e (taught as a pattern, e.g. "have", "since")
    _g("ve", "V"),
    _g("ce", "S"),
    _g("se", "S", "Z"),
    _g("ge", "JH"),
]

UNIVERSAL: dict[str, Gpc] = {g.grapheme: g for g in _LIST}

# Final "s" may say /z/ (dogs, his). Applied by the checker, only when "s" is taught.
FINAL_S_Z: Reading = ("Z",)

# Plain-language labels for sounds, used in reasons shown to teachers.
PHONEME_LABEL: dict[str, str] = {
    "AE": "short a",
    "EH": "short e",
    "IH": "short i",
    "AA": "short o",
    "AO": "aw / short o",
    "AH": "short u",
    "EY": "long a",
    "IY": "long e",
    "AY": "long i",
    "OW": "long o",
    "UW": "oo (long u)",
    "UH": "short oo",
    "AW": "ow",
    "OY": "oy",
    "ER": "er",
    "SH": "sh",
    "CH": "ch",
    "TH": "th",
    "DH": "th (voiced)",
    "NG": "ng",
    "JH": "j",
    "ZH": "zh",
    "HH": "h",
    "Y": "y",
}


def label(phoneme: str) -> str:
    return PHONEME_LABEL.get(phoneme, phoneme.lower())


def reading_label(reading: Reading) -> str:
    return " + ".join(label(p) for p in reading)
