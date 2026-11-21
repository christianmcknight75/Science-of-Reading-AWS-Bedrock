"""Why is a kid stuck? Pattern rules over (word, what the child said) pairs. Plain code, no AI.

DRAFT: these rules stand in for the SME's error-pattern list (open question 22). They look only
at spelling, never at a child's identity; pairs are not stored.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass

_DIGRAPHS = ("sh", "ch", "th", "ck", "ng", "wh")
_VOWELS = set("aeiou")


@dataclass(frozen=True)
class Pattern:
    id: str
    name: str  # plain-language description of what the child does
    skill: str  # what to practice
    query: str  # what to look up in the research library
    also_watch: str  # plain sentence, shown as an idea (not research)


PATTERNS: dict[str, Pattern] = {
    p.id: p
    for p in [
        Pattern(
            "dropped_ending",
            "Reads the start of the word, then stops before the end",
            "Blending through the whole word",
            "teaching students to blend all the sounds in a word left to right",
            "Cover the end of the word and uncover one sound at a time while blending.",
        ),
        Pattern(
            "added_sounds",
            "Adds sounds that are not in the word",
            "Looking at every letter",
            "teaching students to decode by attending to every letter in a word",
            "Have the child point under each letter as they say its sound.",
        ),
        Pattern(
            "sound_order",
            "Mixes up the order of the sounds",
            "Blending sounds in order, left to right",
            "teaching students to blend letter sounds in order to read words",
            "Use sound boxes or a finger sweep from left to right.",
        ),
        Pattern(
            "vowel_sound",
            "Gets the vowel sound wrong",
            "Short vowel sounds",
            "explicit instruction in vowel letter-sound correspondences",
            "Practice vowel sounds in a quick warm-up before reading words.",
        ),
        Pattern(
            "digraph",
            "Reads two letters that make one sound as two separate sounds",
            "Digraphs (sh, ch, th)",
            "explicit systematic phonics instruction digraphs letter-sound correspondences",
            "Show the digraph as one tile or underline it so it reads as one sound.",
        ),
        Pattern(
            "beginning_sound",
            "Gets the first sound wrong but the rest right",
            "Letter-sound knowledge",
            "teaching letter-sound correspondences explicit instruction",
            "Check that the first letter's sound is known on its own, away from words.",
        ),
        Pattern(
            "first_letter_guess",
            "Looks at the first letter, then guesses the rest",
            "Decoding the whole word instead of guessing",
            "teaching decoding instead of guessing words from context or first letters",
            "Ask the child to sound out the word before using the sentence to check it.",
        ),
    ]
}


@dataclass(frozen=True)
class StuckAnalysis:
    pattern: Pattern
    count: int
    total: int  # pairs with an actual mistake


def classify(word: str, said: str) -> str | None:
    """Pattern id for one pair, or None when the pair is not a mistake or matches no rule."""
    w, s = word.lower(), said.lower()
    if w == s or not w or not s:
        return None
    if w.startswith(s):
        return "dropped_ending"
    if s.startswith(w):
        return "added_sounds"
    if sorted(w) == sorted(s):
        return "sound_order"
    if len(w) == len(s) and w[0] == s[0] and w[-1] == s[-1]:
        diff = [i for i in range(len(w)) if w[i] != s[i]]
        if diff and all(w[i] in _VOWELS and s[i] in _VOWELS for i in diff):
            return "vowel_sound"
    if any(d in w and d not in s for d in _DIGRAPHS):
        return "digraph"
    if len(w) > 1 and len(s) > 1 and w[0] != s[0] and w[1:] == s[1:]:
        return "beginning_sound"
    if w[0] == s[0] and w[1:] != s[1:]:
        return "first_letter_guess"
    return None


def analyze(pairs: list[tuple[str, str]]) -> StuckAnalysis | None:
    """The pattern that explains at least half of the mistakes, or None."""
    mistakes = [(w, s) for w, s in pairs if w.lower() != s.lower()]
    found = Counter(p for w, s in mistakes if (p := classify(w, s)))
    if not found:
        return None
    pid, n = found.most_common(1)[0]
    if n < math.ceil(len(mistakes) / 2):
        return None
    return StuckAnalysis(PATTERNS[pid], n, len(mistakes))


WORD = re.compile(r"^[A-Za-z']{1,20}$")
