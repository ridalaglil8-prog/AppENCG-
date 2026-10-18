"""Chargement des données de démonstration — NextStep Maroc.

Le jeu de données vit dans ``data/demo_data.json`` et porte son propre
avertissement. Ce module l'insère de façon **idempotente** : relancer le seed
ne duplique rien et ne modifie jamais une fiche existante.

Règle appliquée : aucun établissement réel ne reçoit de date de concours, de
frais ou de critère d'admission. Seul l'établissement fictif du jeu (statut
``demo``) porte des valeurs d'exemple, clairement étiquetées.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.connection import BASE_DIR, db_session, get_database
from database.models import (
    VERIFICATION_UNKNOWN,
    AdmissionCriterion,
    AdmissionRule,
    Deadline,
    Program,
    Quiz,
    QuizOption,
    QuizQuestion,
    Resource,
    School,
)

DEMO_DATA_PATH = BASE_DIR / "data" / "demo_data.json"


def load_demo_data(path: Optional[Path] = None) -> dict[str, Any]:
    """Insère le jeu de démonstration. Retourne les compteurs d'éléments ajoutés."""
    json_path = Path(path) if path else DEMO_DATA_PATH
    with json_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    with db_session() as session:
        counts = _insert_payload(session, payload)
    return counts


def _insert_payload(session: Session, payload: dict[str, Any]) -> dict[str, int]:
    counts = {"schools": 0, "programs": 0, "rules": 0, "criteria": 0, "deadlines": 0, "quizzes": 0, "questions": 0, "resources": 0}

    school_by_ref: dict[str, int] = {}
    for item in payload.get("schools", []):
        existing = session.scalar(select(School).where(School.name == item["name"]))
        if existing is not None:
            school_by_ref[item["ref"]] = existing.id
            continue
        school = School(
            name=item["name"],
            short_name=item.get("short_name"),
            city=item.get("city"),
            school_type=item.get("school_type"),
            domain=item.get("domain"),
            description=item.get("description"),
            official_url=item.get("official_url"),
            verification_status=item.get("verification_status") or VERIFICATION_UNKNOWN,
            last_verified_at=_parse_date(item.get("last_verified_at")),
        )
        session.add(school)
        session.flush()
        school_by_ref[item["ref"]] = school.id
        counts["schools"] += 1

    program_by_ref: dict[str, int] = {}
    for item in payload.get("programs", []):
        school_id = school_by_ref.get(item["school_ref"])
        if school_id is None:
            continue
        existing = session.scalar(
            select(Program).where(Program.school_id == school_id, Program.name == item["name"])
        )
        if existing is not None:
            program_by_ref[item["ref"]] = existing.id
            continue
        program = Program(
            school_id=school_id,
            name=item["name"],
            degree_level=item.get("degree_level"),
            domain=item.get("domain"),
            duration_years=item.get("duration_years"),
            teaching_language=item.get("teaching_language"),
            description=item.get("description"),
            tuition_fees_mad=item.get("tuition_fees_mad"),
            tuition_note=item.get("tuition_note"),
            official_url=item.get("official_url"),
            verification_status=item.get("verification_status") or VERIFICATION_UNKNOWN,
            last_verified_at=_parse_date(item.get("last_verified_at")),
        )
        session.add(program)
        session.flush()
        program_by_ref[item["ref"]] = program.id
        counts["programs"] += 1

    for item in payload.get("admission_rules", []):
        program_id = program_by_ref.get(item["program_ref"])
        if program_id is None:
            continue
        label = item.get("label") or "Critères"
        existing = session.scalar(
            select(AdmissionRule).where(AdmissionRule.program_id == program_id, AdmissionRule.label == label)
        )
        if existing is not None:
            continue
        rule = AdmissionRule(
            program_id=program_id,
            label=label,
            source_name=item.get("source_name"),
            source_url=item.get("source_url"),
            verification_status=item.get("verification_status") or VERIFICATION_UNKNOWN,
            notes=item.get("notes"),
        )
        session.add(rule)
        session.flush()
        counts["rules"] += 1
        for criterion in item.get("criteria", []):
            session.add(
                AdmissionCriterion(
                    rule_id=rule.id,
                    criterion_type=criterion["criterion_type"],
                    value=criterion["value"],
                    operator=criterion.get("operator"),
                    is_required=bool(criterion.get("is_required", True)),
                    description=criterion.get("description"),
                    verification_status=criterion.get("verification_status") or VERIFICATION_UNKNOWN,
                )
            )
            counts["criteria"] += 1

    for item in payload.get("deadlines", []):
        school_id = school_by_ref.get(item.get("school_ref") or "")
        program_id = program_by_ref.get(item.get("program_ref") or "")
        event_date = _parse_date(item.get("event_date"))
        existing = session.scalar(
            select(Deadline).where(
                Deadline.title == item["title"],
                Deadline.school_id == (school_id or -1),
                Deadline.event_date == event_date,
            )
        )
        if existing is not None:
            continue
        session.add(
            Deadline(
                school_id=school_id,
                program_id=program_id,
                title=item["title"],
                deadline_type=item.get("deadline_type") or "autre",
                event_date=event_date,
                source_name=item.get("source_name"),
                source_url=item.get("source_url"),
                verification_status=item.get("verification_status") or VERIFICATION_UNKNOWN,
            )
        )
        counts["deadlines"] += 1

    for item in payload.get("quizzes", []):
        existing = session.scalar(select(Quiz).where(Quiz.title == item["title"]))
        if existing is not None:
            continue
        quiz = Quiz(
            title=item["title"],
            subject=item["subject"],
            description=item.get("description"),
            language=item.get("language") or "fr",
            difficulty=item.get("difficulty"),
            provenance=item.get("provenance"),
            validation_status=item.get("validation_status") or "demo",
        )
        session.add(quiz)
        session.flush()
        for position, question in enumerate(item.get("questions", []), start=1):
            row = QuizQuestion(
                quiz_id=quiz.id,
                statement=question["statement"],
                explanation=question.get("explanation"),
                difficulty=question.get("difficulty"),
                language=quiz.language,
                provenance=item.get("provenance"),
                validation_status=item.get("validation_status") or "demo",
                position=position,
            )
            session.add(row)
            session.flush()
            for option_position, text in enumerate(question["options"], start=1):
                session.add(
                    QuizOption(
                        question_id=row.id,
                        text=text,
                        is_correct=(option_position - 1) == int(question["correct_index"]),
                        position=option_position,
                    )
                )
        counts["quizzes"] += 1
        counts["questions"] += len(item.get("questions", []))

    for item in payload.get("resources", []):
        existing = session.scalar(select(Resource).where(Resource.title == item["title"]))
        if existing is not None:
            continue
        session.add(
            Resource(
                title=item["title"],
                description=item.get("description"),
                category=item.get("category"),
                language=item.get("language") or "fr",
                author_name=item.get("author_name"),
                source_url=item.get("source_url"),
                content=item.get("content"),
                status=item.get("status") or "pending",
                is_demo=bool(item.get("is_demo", True)),
            )
        )
        counts["resources"] += 1

    session.flush()
    return counts


def _parse_date(value: Any) -> Optional[dt.date]:
    if not value:
        return None
    try:
        return dt.date.fromisoformat(str(value))
    except ValueError:
        return None


def demo_data_is_loaded() -> bool:
    """Vrai si le jeu de démonstration est déjà présent (au moins une école)."""
    try:
        with db_session() as session:
            return session.scalar(select(School).limit(1)) is not None
    except Exception:  # pragma: no cover - base indisponible
        return False


def seed_if_requested() -> dict[str, Any] | None:
    """Charge le jeu de démo si ``NEXTSTEP_SEED_DEMO_DATA`` vaut ``true``."""
    import os

    if os.environ.get("NEXTSTEP_SEED_DEMO_DATA", "").strip().lower() in {"1", "true", "yes", "on"}:
        return load_demo_data()
    return None


if __name__ == "__main__":  # pragma: no cover
    init = get_database()
    init.create_schema()
    print("Seed démonstration :", load_demo_data())
