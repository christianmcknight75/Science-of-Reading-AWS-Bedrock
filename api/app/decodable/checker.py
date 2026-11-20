"""Decodability checker: is a word spelled only with sounds the teacher has taught?

Plain code, no AI. For each word it looks up the CMU Pronouncing Dictionary pronunciation and
tries to line the spelling up with it, grapheme by grapheme, using only the graphemes the
teacher has taught (backtracking search). Result per word:

  decodable      every letter is explained by a taught grapheme
  heart_word     not decodable, but on the teacher's explicit heart-word list (allowed, never
                 labelled "decodable")
  not_decodable  needs an untaught grapheme, or its spelling is irregular
  unknown        not in the dictionary (or contains a symbol): cannot be checked, so not allowed
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path
from typing import Any

from .gpc import FINAL_S_Z, UNIVERSAL, Gpc, Reading, reading_label

SEED_DIR = Path(__file__).resolve().parents[2] / "seed"
_NON_LETTER = re.compile(r"[^a-z]")

# (letters shown, taught grapheme it counts as, sounds used)
Step = tuple[str, str, Reading]


class UnknownGrapheme(ValueError):
    def __init__(self, names: list[str]) -> None:
        super().__init__("unknown grapheme(s): " + ", ".join(names))
        self.names = names


@dataclass(frozen=True)
class WordCheck:
    word: str
    status: str  # decodable | heart_word | not_decodable | unknown
    decodable: bool  # True only for status "decodable"
    reason: str
    graphemes: list[str] = field(default_factory=list)  # how a decodable word breaks up
    needs: list[str] = field(default_factory=list)  # untaught graphemes a failing word needs

    @property
    def allowed(self) -> bool:
        """May appear in a decodable text: decodable, or a listed heart word."""
        return self.status in ("decodable", "heart_word")


@cache
def _cmu() -> Mapping[str, list[list[str]]]:
    import cmudict

    return {
        w: [[p.rstrip("012") for p in pron] for pron in prons]
        for w, prons in cmudict.dict().items()
    }


def normalize_taught(tokens: Iterable[str]) -> list[str]:
    seen: dict[str, None] = {}
    unknown: list[str] = []
    for t in tokens:
        g = t.strip().lower()
        if len(g) == 2 and g[0] == g[1] and g[0] in UNIVERSAL and not UNIVERSAL[g[0]].vowel:
            g = g[0]  # "ff", "ll", "ss", "zz": doubles are covered by the single consonant
        if g in UNIVERSAL:
            seen[g] = None
        elif g:
            unknown.append(t)
    if unknown:
        raise UnknownGrapheme(unknown)
    return list(seen)


class DecodabilityChecker:
    def __init__(
        self,
        taught: Iterable[str],
        heart_words: Iterable[str] = (),
        pronunciations: Mapping[str, list[list[str]]] | None = None,
    ) -> None:
        self.taught: frozenset[str] = frozenset(normalize_taught(taught))
        self.heart_words: frozenset[str] = frozenset(w.strip().lower() for w in heart_words)
        self._pron = pronunciations if pronunciations is not None else _cmu()

    # ------------------------------------------------------------------ public
    def check(self, word: str) -> WordCheck:
        w = word.strip().lower()
        if not w:
            return WordCheck(word, "unknown", False, "Empty word.")
        if _NON_LETTER.search(w):
            if w in self.heart_words:
                return self._heart(word)
            return WordCheck(
                word,
                "unknown",
                False,
                "Has an apostrophe, number or symbol, so it cannot be checked.",
            )
        prons = self._pron.get(w)
        if not prons:
            if w in self.heart_words:
                return self._heart(word)
            return WordCheck(
                word,
                "unknown",
                False,
                "Not in the pronunciation dictionary, so it cannot be checked.",
            )
        taught_table = {g: UNIVERSAL[g] for g in self.taught}
        for pron in prons:
            found = _search(w, tuple(pron), taught_table, self.taught)
            if found is not None:
                graphemes = [shown for shown, _, _ in found[1]]
                return WordCheck(
                    word,
                    "decodable",
                    True,
                    "Sounds out with taught sounds: " + " + ".join(graphemes) + ".",
                    graphemes=graphemes,
                )
        if w in self.heart_words:
            return self._heart(word)
        return self._explain(word, w, prons)

    def check_text(self, words: Iterable[str]) -> list[WordCheck]:
        return [self.check(w) for w in words]

    # ------------------------------------------------------------------ helpers
    def _heart(self, word: str) -> WordCheck:
        return WordCheck(
            word,
            "heart_word",
            False,
            "Not decodable with the taught sounds. Allowed because it is on your heart-word list.",
        )

    def _explain(self, word: str, w: str, prons: list[list[str]]) -> WordCheck:
        """Which untaught graphemes would make this word decodable?"""
        best: tuple[int, tuple[Step, ...]] | None = None
        for pron in prons:
            found = _search(w, tuple(pron), UNIVERSAL, self.taught)
            if found is not None and (best is None or found[0] < best[0]):
                best = found
        if best is None:
            return WordCheck(
                word,
                "not_decodable",
                False,
                "Its spelling does not follow the usual letter-sound patterns, so teach it as a "
                "heart word.",
            )
        needs: dict[str, str] = {}
        for _shown, base, reading in best[1]:
            if base not in self.taught:
                needs.setdefault(base, reading_label(reading))
        parts = ", ".join(f"'{g}' ({lab})" for g, lab in needs.items())
        return WordCheck(
            word,
            "not_decodable",
            False,
            f"Needs {parts}, which you have not taught yet.",
            needs=list(needs),
        )


def _candidates(word: str, i: int, table: Mapping[str, Gpc]) -> list[tuple[Gpc, str, int]]:
    """Graphemes that start at position i: (gpc, letters shown, letters used), longest first."""
    out: list[tuple[Gpc, str, int]] = []
    for g in table.values():
        o = g.orth
        if word.startswith(o, i):
            out.append((g, g.grapheme if g.split else o, len(o)))
        single_consonant = len(o) == 1 and not g.vowel and not g.split
        if single_consonant and word.startswith(o * 2, i):
            out.append((g, o * 2, 2))  # doubled consonant counts as the single consonant
    out.sort(key=lambda c: -c[2])
    return out


def _search(
    word: str, pron: tuple[str, ...], table: Mapping[str, Gpc], taught: frozenset[str]
) -> tuple[int, tuple[Step, ...]] | None:
    """Cheapest way to spell `pron` as `word` with graphemes from `table`.

    Cost = number of graphemes not in `taught`. With the taught table it is 0 or no match.
    """
    n = len(word)

    @cache
    def go(i: int, p: int, pending: bool) -> tuple[int, tuple[Step, ...]] | None:
        if pending and i == n - 1:  # the silent e of a split digraph
            return go(n, p, False) if word[i] == "e" else None
        if i == n:
            return (0, ()) if p == len(pron) and not pending else None
        best: tuple[int, tuple[Step, ...]] | None = None
        for g, shown, used in _candidates(word, i, table):
            if pending and (g.vowel or g.split or i + used > n - 1):
                continue
            if g.split and (not word.endswith("e") or i + used > n - 2):
                continue
            readings: tuple[Reading, ...] = g.readings
            if g.grapheme == "s" and i == n - 1 and n >= 3:
                readings = readings + (FINAL_S_Z,)
            base = g.grapheme
            cost = 0 if base in taught else 1
            for r in readings:
                if pron[p : p + len(r)] != r:
                    continue
                rest = go(i + used, p + len(r), pending or g.split)
                if rest is None:
                    continue
                cand = (cost + rest[0], ((shown, base, r), *rest[1]))
                if best is None or cand[0] < best[0]:
                    best = cand
                if best[0] == 0:
                    return best
        return best

    return go(0, 0, False)


# ---------------------------------------------------------------------- seed data
def load_scope(path: Path | None = None) -> list[dict[str, Any]]:
    """Ordered phonics scope and sequence (the `grapheme_scope` table's content)."""
    data: list[dict[str, Any]] = json.loads((path or SEED_DIR / "grapheme_scope.json").read_text())
    return sorted(data, key=lambda r: r["position"])


def taught_through(scope: list[dict[str, Any]], position: int) -> list[str]:
    return [r["grapheme"] for r in scope if r["position"] <= position]


def load_heart_words(path: Path | None = None) -> list[str]:
    data: dict[str, Any] = json.loads((path or SEED_DIR / "heart_words.json").read_text())
    return [w.lower() for w in data["words"]]
