"""Service de préparation aux concours (QCM, scores, progression).

Points importants :
* la **correction n'est jamais calculée côté client** : ``submit_attempt``
  recalcule chaque réponse à partir de la base ;
* l'historique n'est enregistré que lorsque l'utilisateur est connecté ;
* les contenus de démonstration sont explicitement marqués (``provenance``,
  ``validation_status``) : ce ne sont pas des sujets officiels de concours.
"""

from __future__ import annotations

from typing import Any, Optional, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from database import repositories as repo
from database.models import Quiz, QuizAttempt, User, utcnow
from utils.exceptions import BusinessValidationError, NotFoundError


def available_quizzes(session: Session, language: Optional[str] = None) -> list[Quiz]:
    """QCM actifs, groupés par matière côté UI."""
    return repo.list_quizzes(session, language=language)


def get_quiz(session: Session, quiz_id: int) -> Quiz:
    quiz = repo.get_quiz(session, quiz_id)
    if quiz is None or not quiz.is_active:
        raise NotFoundError("error_not_found")
    return quiz


def question_payload(quiz: Quiz, index: int) -> dict[str, Any]:
    """Question ``index`` (0-based) **sans** la bonne réponse (anti-triche)."""
    questions = list(quiz.questions)
    if index < 0 or index >= len(questions):
        raise NotFoundError("error_not_found")
    question = questions[index]
    return {
        "id": question.id,
        "position": question.position,
        "statement": question.statement,
        "difficulty": question.difficulty,
        "language": question.language,
        "provenance": question.provenance,
        "validation_status": question.validation_status,
        "options": [{"id": option.id, "text": option.text} for option in question.options],
        "index": index,
        "total": len(questions),
    }


def validate_answer(session: Session, question_id: int, option_id: int) -> dict[str, Any]:
    """Corrige une réponse : retourne correction, explication et réponse attendue."""
    from database.models import QuizOption, QuizQuestion

    question = session.scalar(
        select(QuizQuestion)
        .options(selectinload(QuizQuestion.options))
        .where(QuizQuestion.id == question_id)
    )
    if question is None:
        raise NotFoundError("error_not_found")
    option = session.get(QuizOption, option_id)
    if option is None or option.question_id != question.id:
        raise BusinessValidationError("error_validation", ["option: inconnue"])

    correct_option = next((o for o in question.options if o.is_correct), None)
    return {
        "question_id": question.id,
        "chosen_option_id": option.id,
        "chosen_text": option.text,
        "is_correct": bool(option.is_correct),
        "correct_option_id": correct_option.id if correct_option else None,
        "correct_text": correct_option.text if correct_option else "",
        "explanation": question.explanation or "",
        "statement": question.statement,
    }


def score_answers(quiz: Quiz, answers: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Calcule un score **sans** persistance (utilisable hors connexion).

    ``answers`` : liste de ``{"question_id": int, "option_id": int}``.
    La correction utilise uniquement les options ``is_correct`` de la base.
    """
    questions = {q.id: q for q in quiz.questions}
    corrections: list[dict[str, Any]] = []
    answered_ids: set[int] = set()
    score = 0

    for answer in answers:
        question = questions.get(int(answer.get("question_id", 0)))
        if question is None:
            continue
        option_id = int(answer.get("option_id", 0))
        chosen = next((o for o in question.options if o.id == option_id), None)
        correct = next((o for o in question.options if o.is_correct), None)
        is_correct = bool(chosen is not None and chosen.is_correct)
        if is_correct:
            score += 1
        answered_ids.add(question.id)
        corrections.append(
            {
                "question_id": question.id,
                "statement": question.statement,
                "chosen_text": chosen.text if chosen else "",
                "is_correct": is_correct,
                "correct_text": correct.text if correct else "",
                "explanation": question.explanation or "",
            }
        )

    total = len(questions)
    # Les questions non répondues comptent comme non acquises.
    for question in questions.values():
        if question.id not in answered_ids:
            correct = next((o for o in question.options if o.is_correct), None)
            corrections.append(
                {
                    "question_id": question.id,
                    "statement": question.statement,
                    "chosen_text": "",
                    "is_correct": False,
                    "correct_text": correct.text if correct else "",
                    "explanation": question.explanation or "",
                }
            )

    return {
        "score": score,
        "total": total,
        "pct": round(100.0 * score / total, 1) if total else 0.0,
        "corrections": corrections,
    }


def submit_attempt(
    session: Session,
    user_id: Optional[int],
    quiz_id: int,
    answers: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    """Calcule et, si connecté, enregistre la tentative (+ journal d'audit)."""
    quiz = get_quiz(session, quiz_id)
    result = score_answers(quiz, answers)

    attempt: Optional[QuizAttempt] = None
    if user_id:
        attempt = QuizAttempt(
            user_id=user_id,
            quiz_id=quiz.id,
            answers={str(a.get("question_id")): {"option_id": a.get("option_id")} for a in answers},
            score=result["score"],
            total=result["total"],
            started_at=None,
            finished_at=utcnow(),
        )
        session.add(attempt)
        session.flush()
        repo.add_audit_log(
            session,
            actor_id=user_id,
            action="quiz.attempt",
            entity_type="quiz",
            entity_id=quiz.id,
            detail={"score": result["score"], "total": result["total"]},
        )
        result["attempt_id"] = attempt.id
    result["saved"] = attempt is not None
    return result


def history(session: Session, user_id: int, quiz_id: Optional[int] = None) -> list[QuizAttempt]:
    return repo.list_attempts(session, user_id, quiz_id=quiz_id)


def progress(session: Session, user_id: int) -> list[dict[str, Any]]:
    """Progression par matière (tentatives, meilleur pourcentage, dernière date)."""
    return repo.progress_by_subject(session, user_id)


def latest_attempts(session: Session, user_id: int, limit: int = 5) -> list[QuizAttempt]:
    return repo.list_attempts(session, user_id, limit=limit)


__all__ = [
    "available_quizzes",
    "get_quiz",
    "history",
    "latest_attempts",
    "progress",
    "question_payload",
    "score_answers",
    "submit_attempt",
    "validate_answer",
]
