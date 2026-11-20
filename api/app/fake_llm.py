"""A stand-in model for local development while Bedrock is blocked (OPEN_QUESTIONS 15).

`LLM_MODE=fake` makes the API use this instead of Bedrock, so the whole stack (retrieval, verifier,
labels, decodability checker, accounts) can be driven end to end from the web app. It is NOT a
model: it quotes the first passage it is shown, word for word, so the real verifier passes it, and
everything it writes is labelled "[Fake model]". It refuses to run with Cognito auth.
"""

from __future__ import annotations

import re
from typing import Any

from .decodable import DecodabilityChecker
from .llm import LLMResult, ToolSpec

LABEL = "[Fake model] "
_PASSAGE = re.compile(r'<passage id="([^"]+)"[^>]*>\n(.*?)\n</passage>', re.S)
_ASCII = re.compile(r"^[A-Za-z0-9 ,.;:!?'\"()\-]+$")
WORDS = (
    "cat sat mat pat sam tin pin sit pit nap map tap tip sip nip man pan can ran fan fat hat "
    "bat rat dad mad sad had hid did dig big pig fig fin sin win hit fit bit kit lap cap gap "
    "ham jam dim him hip lip rip zip bug hug mud rug sun fun run bun cup pup hot dot pot mop "
    "top hop cob job fox box six mix wet pet net men hen ten leg peg bed red fed beg"
).split()
FALLBACK = "Pat sat in a tin. It is a big tin. Pat has a hat."


def _first_quote(user: str) -> tuple[str, str] | None:
    """(passage id, 12 plain words) from the first passage that has such a stretch of text."""
    for pid, text in _PASSAGE.findall(user):
        words = text.split()
        for i in range(0, min(len(words) - 12, 250)):
            window = " ".join(words[i : i + 12])
            if _ASCII.match(window):
                return pid, window
    return None


def _allowed(user: str) -> tuple[list[str], list[str]]:
    sounds = re.search(r"Allowed sounds: (.*)", user)
    hearts = re.search(r"Allowed heart words: (.*)", user)
    return (
        [s.strip() for s in sounds.group(1).split(",") if s.strip()] if sounds else [],
        []
        if not hearts or hearts.group(1).strip() == "none"
        else [h.strip() for h in hearts.group(1).split(",") if h.strip()],
    )


def _story(user: str) -> dict[str, str]:
    """Short word-list sentences from words the checker accepts for the taught sounds."""
    sounds, hearts = _allowed(user)
    version = re.search(r"Version: (\d+)", user)
    start = (int(version.group(1)) - 1) * 5 if version else 0
    try:
        checker = DecodabilityChecker(sounds, hearts)
    except ValueError:
        return {"title": "Fake story", "text": FALLBACK}
    ok = [w for w in WORDS if checker.check(w).decodable]
    if len(ok) < 6:  # too few sounds: hand back something that may fail the check
        return {"title": "Fake story", "text": FALLBACK}
    picked = [ok[(start + i) % len(ok)] for i in range(9)]
    lines = [" ".join(picked[i : i + 3]).capitalize() + "." for i in range(0, 9, 3)]
    return {"title": "Fake story", "text": " ".join(lines)}


def _steps(user: str) -> list[dict[str, Any]]:
    return [
        {
            "title": f"{LABEL}Warm up",
            "minutes": 3,
            "body": "Say each sound, then have the group repeat it.",
            "sounds": ["s", "a", "t"],
        },
        {
            "title": f"{LABEL}Blend words",
            "minutes": 5,
            "body": "Slide a finger under the letters and blend the sounds.",
            "words": ["cat", "sat", "ship", "dog"],
            "tip": "Keep it quick and cheerful.",
            "alt": {"title": f"{LABEL}Sound boxes", "body": "Push one counter per sound."},
        },
        {
            "title": f"{LABEL}Read a story",
            "minutes": 4,
            "body": "Read a short story with the sounds you practised.",
        },
    ]


def _idea(properties: dict[str, Any], user: str) -> dict[str, Any]:
    if "steps" in properties:
        return {"steps": _steps(user)}
    if "try_it" in properties:
        return {
            "try_it": {"text": f"{LABEL}Sort picture cards by their first sound.", "minutes": 5}
        }
    if "short_idea" in properties:
        shape = {
            "title": f"{LABEL}Sound sweep",
            "minutes": 10,
            "steps": ["Say a sound.", "Blend."],
            "need": "Letter cards",
        }
        return {
            "remember_sounds": [{"letter": "s", "hint": "snake"}],
            "remember_tip": f"{LABEL}Keep practice short.",
            "idea": shape,
            "short_idea": {**shape, "minutes": 5},
            "if_stuck": f"{LABEL}Slow down and model it.",
            "if_easy": f"{LABEL}Add a harder word.",
            "for_english_learners": f"{LABEL}Use pictures for each word.",
        }
    return {}


class LocalFakeLLM:
    def converse(
        self, *, model_id: str, system: str, user: str, max_tokens: int, tool: ToolSpec
    ) -> LLMResult:
        if tool.name == "submit_checks":
            n = user.count("<claim index=")
            checks = [{"index": i, "verdict": "supported"} for i in range(n)]
            return LLMResult({"checks": checks}, "", 400, 40)
        if tool.name == "submit_story":
            return LLMResult(_story(user), "", 200, 60)
        quote = _first_quote(user)
        if quote is None:
            return LLMResult({"answerable": False, "claims": []}, "", 300, 10)
        pid, window = quote
        claim = {"text": f'{LABEL}A source says: "{window}"', "passage_ids": [pid], "quote": window}
        payload: dict[str, Any] = {"answerable": True, "claims": [claim]}
        if tool.name == "submit_answer":
            payload["steps"] = [
                {"text": f"{LABEL}Try a 5-minute warm-up with your group.", "minutes": 5}
            ]
        else:
            props = tool.schema.get("properties", {}).get("idea", {}).get("properties", {})
            payload["idea"] = _idea(props, user)
        return LLMResult(payload, "", 3000, 200)
