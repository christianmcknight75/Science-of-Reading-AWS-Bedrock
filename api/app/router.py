"""Rule-based router (no model call). Sends out-of-scope questions to an honest refusal.

Out of scope (CLAUDE.md rule 6): promotion/retention and other student-specific decisions,
product or curriculum endorsement, teacher evaluation. Bedrock Guardrails is a second layer.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_DECISION = re.compile(
    r"\b(retain|retention|hold(ing)? (him|her|them|a child|a student|\w+) back|held back|"
    r"promot(e|ed|ion)|repeat(ing)? (the )?(grade|kindergarten|first|second|third)|"
    r"flunk|iep eligib\w*|qualif(y|ies) for (an )?(iep|special education)|"
    r"diagnos(e|is|ing)|does (he|she|this \w+|my \w+|\w+) have dyslexia)\b",
    re.I,
)
_EVALUATIVE = re.compile(
    r"\b(best|better|worst|recommend\w*|which|top|worth|good|buy|purchase|choose|endorse\w*|"
    r"compare|versus|vs)\b",
    re.I,
)
_PRODUCT = re.compile(
    r"\b(program|curriculum|product|app|software|vendor|brand|series|kit|publisher|"
    r"heggerty|lexia|iready|i-ready|fundations|ufli|wilson|orton|lli|reading mastery|saxon|"
    r"amplify|wonders|benchmark|calkins|units of study|fountas|pinnell|reading recovery|"
    r"read ?180|istation|letrs|acadience|dibels|star reading|renaissance)\b",
    re.I,
)
_EVALUATION = re.compile(
    r"\b(evaluat\w+|rate|grade|score|critique|judge|assess)\s+(me|my (teaching|lesson|performance|"
    r"class(room)?))\b|\bam i (a )?(good|bad|doing)\b|\bis my teaching\b|\bteacher evaluation\b",
    re.I,
)


@dataclass(frozen=True)
class Route:
    kind: str  # "answer" | "out_of_scope" | "clarify"
    reason: str = ""
    reply: str = ""


def route(question: str) -> Route:
    q = question.strip()
    if len(q.split()) < 3:
        return Route(
            "clarify",
            "too_short",
            "Could you say a little more? For example: 'How do I teach blending to "
            "kindergartners?'",
        )
    if _DECISION.search(q):
        return Route(
            "out_of_scope",
            "student_decision",
            "I can't help with decisions about a child, such as retention, promotion, placement "
            "or diagnosis. Those belong with your school team. I can share research on teaching "
            "and supporting readers.",
        )
    if _EVALUATION.search(q):
        return Route(
            "out_of_scope",
            "teacher_evaluation",
            "I don't rate or evaluate teachers or lessons. I can share research that may help "
            "you plan instruction.",
        )
    if _PRODUCT.search(q) and _EVALUATIVE.search(q):
        return Route(
            "out_of_scope",
            "product_endorsement",
            "I don't recommend or compare specific programs, curricula or products. I can share "
            "what research says about the teaching practices behind them.",
        )
    return Route("answer")
