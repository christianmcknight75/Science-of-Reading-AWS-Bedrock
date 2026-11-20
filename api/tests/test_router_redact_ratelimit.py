import pytest

from app.ratelimit import RateLimiter
from app.redact import PresidioRedactor
from app.router import route


@pytest.mark.parametrize(
    ("question", "reason"),
    [
        ("Should I retain my struggling reader in first grade?", "student_decision"),
        ("Does this child have dyslexia?", "student_decision"),
        ("Please evaluate my teaching of phonics", "teacher_evaluation"),
        ("Am I a good reading teacher?", "teacher_evaluation"),
        ("Which is the best phonics program to buy?", "product_endorsement"),
        ("Is Lexia better than Fundations?", "product_endorsement"),
    ],
)
def test_out_of_scope_questions_are_refused(question: str, reason: str) -> None:
    r = route(question)
    assert r.kind == "out_of_scope" and r.reason == reason and r.reply


@pytest.mark.parametrize(
    "question",
    [
        "How do I teach blending to kindergartners?",
        "What does research say about phonics programs in general?",  # a topic, not a purchase
        "Why do some children struggle to decode words?",
    ],
)
def test_in_scope_questions_go_through(question: str) -> None:
    assert route(question).kind == "answer"


def test_very_short_question_asks_for_more() -> None:
    assert route("phonics?").kind == "clarify"


def test_rate_limit_allows_then_blocks_then_recovers() -> None:
    now = [0.0]
    rl = RateLimiter(2, 60, clock=lambda: now[0])
    assert rl.allow("a") and rl.allow("a") and not rl.allow("a")
    assert rl.allow("b")  # separate user
    now[0] = 61
    assert rl.allow("a")


def test_presidio_removes_names_schools_contacts_and_ids() -> None:
    text = (
        "My student Jamal Washington at Lincoln Elementary can't blend. "
        "Email jo.smith@example.org or call 601-555-0100. ID 12345678."
    )
    out = PresidioRedactor().redact(text)
    for leaked in ("Jamal", "Washington", "Lincoln", "jo.smith", "555-0100", "12345678"):
        assert leaked not in out
    assert "blend" in out  # the actual question survives


def test_presidio_leaves_a_plain_teaching_question_alone() -> None:
    q = "How do I teach phonemic awareness to kindergartners?"
    assert PresidioRedactor().redact(q) == q
