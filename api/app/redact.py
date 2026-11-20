"""PII redaction before anything is logged or sent to a model (CLAUDE.md rule 2).

Presidio (spaCy small model) finds names, schools, places, emails, phones and IDs; a few regexes
add school-name patterns and long digit runs. Recall matters more than precision here: an
over-redacted question is only slightly worse, a leaked student name is a policy breach.
"""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Protocol

ENTITIES = [
    "PERSON",
    "EMAIL_ADDRESS",
    "PHONE_NUMBER",
    "US_SSN",
    "CREDIT_CARD",
    "IP_ADDRESS",
    "URL",
    "LOCATION",
    "ORGANIZATION",
]
_SCHOOL = re.compile(
    r"\b(?:[A-Z][\w'’.-]*\s+){1,4}(?:Elementary|Primary|Middle|High|Academy|School|District)\b"
)
_LONG_NUMBER = re.compile(r"\b\d{6,}\b")  # student / phone / ID numbers


class Redactor(Protocol):
    def redact(self, text: str) -> str: ...


class PresidioRedactor:
    def __init__(self) -> None:
        from presidio_analyzer import AnalyzerEngine
        from presidio_analyzer.nlp_engine import NlpEngineProvider

        nlp = NlpEngineProvider(
            nlp_configuration={
                "nlp_engine_name": "spacy",
                "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}],
            }
        ).create_engine()
        self._analyzer = AnalyzerEngine(nlp_engine=nlp, supported_languages=["en"])

    def redact(self, text: str) -> str:
        hits = self._analyzer.analyze(text=text, language="en", entities=ENTITIES)
        spans = sorted(((h.start, h.end, h.entity_type) for h in hits), key=lambda s: s[0])
        out: list[str] = []
        pos = 0
        for start, end, kind in spans:
            if start < pos:  # overlapping hit: extend the previous mask, do not double-write
                continue
            out.append(text[pos:start])
            out.append(f"[{kind}]")
            pos = end
        out.append(text[pos:])
        return _regex_pass("".join(out))


def _regex_pass(text: str) -> str:
    text = _SCHOOL.sub("[SCHOOL]", text)
    return _LONG_NUMBER.sub("[NUMBER]", text)


@lru_cache(maxsize=1)
def get_redactor() -> Redactor:
    return PresidioRedactor()
