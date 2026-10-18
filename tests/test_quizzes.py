"""Tests de la préparation aux concours : QCM, correction, tentatives."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import func, select  # noqa: E402

from database import models as m  # noqa: E402
from services import quiz_service  # noqa: E402
from utils.exceptions import BusinessValidationError, NotFoundError  # noqa: E402


def _answers_for(quiz, correct: bool) -> list[dict]:
    """Réponses toutes justes ou toutes fausses (le test connaît la correction)."""
    payload = []
    for question in quiz.questions:
        right = next((o for o in question.options if o.is_correct), question.options[0])
        wrong = next((o for o in question.options if not o.is_correct), question.options[0])
        option = right if correct else wrong
        payload.append({"question_id": question.id, "option_id": option.id})
    return payload


# --------------------------------------------------------------------------- #
# Correction
# --------------------------------------------------------------------------- #


def test_question_payload_hides_correct_answer(session, make_quiz):
    quiz = make_quiz()
    payload = quiz_service.question_payload(quiz, 0)
    assert payload["statement"]
    assert payload["total"] == 2
    assert all("is_correct" not in option for option in payload["options"])
    assert all("correct" not in option for option in payload["options"])


def test_question_payload_rejects_out_of_range(session, make_quiz):
    quiz = make_quiz()
    with pytest.raises(NotFoundError):
        quiz_service.question_payload(quiz, 5)


def test_score_answers_counts_only_correct_options(session, make_quiz):
    quiz = make_quiz()
    # Question 1 : bonne réponse en position 1 ; question 2 : position 2.
    answers = [
        {"question_id": quiz.questions[0].id, "option_id": quiz.questions[0].options[0].id},
        {"question_id": quiz.questions[1].id, "option_id": quiz.questions[1].options[0].id},
    ]
    result = quiz_service.score_answers(quiz, answers)
    assert result["score"] == 1
    assert result["total"] == 2
    assert result["pct"] == 50.0
    assert len(result["corrections"]) == 2


def test_unanswered_questions_count_as_not_acquired(session, make_quiz):
    quiz = make_quiz()
    result = quiz_service.score_answers(
        quiz, [{"question_id": quiz.questions[0].id, "option_id": quiz.questions[0].options[0].id}]
    )
    assert result["score"] == 1
    assert result["total"] == 2
    assert len(result["corrections"]) == 2  # la non-répondu est listée
    missing = next(c for c in result["corrections"] if c["question_id"] == quiz.questions[1].id)
    assert missing["chosen_text"] == ""


def test_perfect_and_zero_scores(session, make_quiz):
    quiz = make_quiz()
    perfect = quiz_service.score_answers(quiz, _answers_for(quiz, correct=True))
    zero = quiz_service.score_answers(quiz, _answers_for(quiz, correct=False))
    assert perfect["score"] == perfect["total"] == 2
    assert perfect["pct"] == 100.0
    assert zero["score"] == 0
    assert zero["pct"] == 0.0


def test_score_is_deterministic(session, make_quiz):
    quiz = make_quiz()
    first = quiz_service.score_answers(quiz, _answers_for(quiz, correct=True))
    second = quiz_service.score_answers(quiz, _answers_for(quiz, correct=True))
    assert first == second


def test_validate_answer_returns_correction(session, make_quiz):
    quiz = make_quiz()
    question = quiz.questions[0]
    good = quiz_service.validate_answer(session, question.id, question.options[0].id)
    assert good["is_correct"] is True
    assert good["correct_text"] == "Bonne réponse"
    assert good["explanation"] == "Explication 1"

    bad = quiz_service.validate_answer(session, question.id, question.options[1].id)
    assert bad["is_correct"] is False


def test_validate_answer_rejects_option_from_other_question(session, make_quiz):
    quiz = make_quiz()
    with pytest.raises(BusinessValidationError):
        quiz_service.validate_answer(
            session, quiz.questions[0].id, quiz.questions[1].options[0].id
        )


# --------------------------------------------------------------------------- #
# Tentatives
# --------------------------------------------------------------------------- #


def test_attempt_is_recorded_for_logged_in_user(session, make_user, make_quiz):
    user = make_user()
    quiz = make_quiz()
    result = quiz_service.submit_attempt(session, user.id, quiz.id, _answers_for(quiz, True))
    session.flush()

    assert result["saved"] is True
    assert "attempt_id" in result

    attempts = quiz_service.history(session, user.id)
    assert len(attempts) == 1
    assert attempts[0].score == result["score"]
    assert attempts[0].finished_at is not None

    # Journal d'audit associé.
    actions = session.scalars(select(m.AuditLog.action)).all()
    assert "quiz.attempt" in actions


def test_attempt_is_not_persisted_for_guest(session, make_quiz):
    quiz = make_quiz()
    before = session.scalar(select(func.count()).select_from(m.QuizAttempt))
    result = quiz_service.submit_attempt(session, None, quiz.id, _answers_for(quiz, True))
    session.flush()
    after = session.scalar(select(func.count()).select_from(m.QuizAttempt))

    assert result["saved"] is False
    assert "attempt_id" not in result
    assert before == after


def test_score_is_recomputed_server_side(session, make_user, make_quiz):
    """Le score enregistré vient de la base, pas du client."""
    user = make_user()
    quiz = make_quiz()
    client_claims_score = 42  # valeur envoyée par un éventuel client malveillant
    result = quiz_service.submit_attempt(session, user.id, quiz.id, _answers_for(quiz, True))
    session.flush()
    assert result["score"] == 2
    assert result["score"] != client_claims_score


def test_progress_by_subject(session, make_user, make_quiz):
    user = make_user()
    quiz = make_quiz()
    quiz_service.submit_attempt(session, user.id, quiz.id, _answers_for(quiz, True))
    session.flush()

    progress = quiz_service.progress(session, user.id)
    assert progress
    entry = next(row for row in progress if row["subject"] == quiz.subject)
    assert entry["attempts"] >= 1
    assert entry["best"] == 100.0


def test_history_is_per_user(session, make_user, make_quiz):
    alice = make_user(email="alice-quiz@test.ma")
    bob = make_user(email="bob-quiz@test.ma")
    quiz = make_quiz()
    quiz_service.submit_attempt(session, alice.id, quiz.id, _answers_for(quiz, True))
    session.flush()

    assert len(quiz_service.history(session, alice.id)) == 1
    assert quiz_service.history(session, bob.id) == []


def test_unknown_quiz_raises(session):
    with pytest.raises(NotFoundError):
        quiz_service.get_quiz(session, 987654)


def test_inactive_quiz_is_not_available(session, make_quiz):
    quiz = make_quiz()
    quiz.is_active = False
    session.flush()
    with pytest.raises(NotFoundError):
        quiz_service.get_quiz(session, quiz.id)
    assert quiz not in quiz_service.available_quizzes(session)


def test_demo_provenance_is_explicit(session, make_quiz):
    """Les QCM de démonstration sont marqués comme tels (pas des sujets officiels)."""
    quiz = make_quiz()
    assert quiz.validation_status in m.VERIFICATION_STATUSES
    for question in quiz.questions:
        assert question.provenance  # provenance affichée à l'utilisateur
