"""Fixtures partagées des tests — NextStep Maroc.

Chaque test travaille sur une **base SQLite temporaire** créée dans ``tmp_path`` :
aucune donnée réelle n'est lue, modifiée ni supprimée. Le hachage bcrypt étant
volontairement coûteux (12 tours), il n'est calculé **qu'une fois** au
démarrage de la session de tests puis réutilisé pour les comptes de test —
le hachage reste valide puisque le sel est intégré au hachage lui-même.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Optional

import pytest

ROOT = Path(__file__).resolve().parents[1]
TESTS_DIR = Path(__file__).resolve().parent
for path in (str(ROOT), str(TESTS_DIR)):
    if path not in sys.path:
        sys.path.insert(0, path)

from database import connection, models as m  # noqa: E402
from helpers import PASSWORD_HASH, TEST_PASSWORD  # noqa: E402


# --------------------------------------------------------------------------- #
# Base de données isolée
# --------------------------------------------------------------------------- #


@pytest.fixture()
def db(tmp_path):
    """Base SQLite temporaire initialisée (schéma créé, jamais de drop)."""
    url = f"sqlite:///{(tmp_path / 'nextstep_test.db').as_posix()}"
    previous = os.environ.get("NEXTSTEP_DATABASE_URL")
    os.environ["NEXTSTEP_DATABASE_URL"] = url
    connection.reset_database()
    database = connection.init_database(url)
    yield database
    connection.reset_database()
    if previous is None:
        os.environ.pop("NEXTSTEP_DATABASE_URL", None)
    else:
        os.environ["NEXTSTEP_DATABASE_URL"] = previous


@pytest.fixture()
def session(db):
    """Session court cycle (commit en fin de test, rollback en cas d'erreur)."""
    with db.session() as active:
        yield active


# --------------------------------------------------------------------------- #
# Fabriques d'objets de test
# --------------------------------------------------------------------------- #


@pytest.fixture()
def make_user(session):
    """Crée un compte de test sans recalculer bcrypt à chaque appel."""
    counter = {"n": 0}

    def _make(
        email: Optional[str] = None,
        role: str = "candidat",
        language: str = "fr",
        active: bool = True,
    ) -> m.User:
        counter["n"] += 1
        user = m.User(
            email=email or f"user{counter['n']}@test.ma",
            password_hash=PASSWORD_HASH,
            role=role,
            language=language,
            is_active=active,
        )
        session.add(user)
        session.flush()
        return user

    return _make


@pytest.fixture()
def make_school(session):
    def _make(name: str = "École de test", **fields: Any) -> m.School:
        payload = {
            "name": name,
            "city": "Casablanca",
            "school_type": "grande école",
            "domain": "gestion",
            "verification_status": m.VERIFICATION_PENDING,
            "is_active": True,
        }
        payload.update(fields)
        school = m.School(**payload)
        session.add(school)
        session.flush()
        return school

    return _make


@pytest.fixture()
def make_program(session):
    def _make(school: m.School, name: str = "Formation de test", **fields: Any) -> m.Program:
        payload = {
            "school_id": school.id,
            "name": name,
            "degree_level": "mastère",
            "domain": "gestion",
            "verification_status": m.VERIFICATION_PENDING,
            "is_active": True,
        }
        payload.update(fields)
        program = m.Program(**payload)
        session.add(program)
        session.flush()
        return program

    return _make


@pytest.fixture()
def make_rule(session):
    """Publie une règle d'admission + ses critères pour une formation."""

    def _make(
        program: m.Program,
        criteria: list[dict[str, Any]],
        status: str = m.VERIFICATION_OFFICIAL,
        label: str = "Critères de test",
    ) -> m.AdmissionRule:
        rule = m.AdmissionRule(
            program_id=program.id,
            label=label,
            source_name="Source de test",
            verification_status=status,
        )
        session.add(rule)
        session.flush()
        for spec in criteria:
            session.add(
                m.AdmissionCriterion(
                    rule_id=rule.id,
                    criterion_type=spec.get("criterion_type", "bac_series"),
                    value=spec.get("value", []),
                    operator=spec.get("operator", "in"),
                    is_required=spec.get("is_required", True),
                    description=spec.get("description"),
                    verification_status=spec.get("verification_status", status),
                )
            )
        session.flush()
        return rule

    return _make


@pytest.fixture()
def make_quiz(session):
    """Crée un QCM avec ses questions et options (index de bonne réponse inclus)."""

    def _make(
        title: str = "QCM de test",
        subject: str = "Mathématiques",
        questions: Optional[list[dict[str, Any]]] = None,
        language: str = "fr",
    ) -> m.Quiz:
        quiz = m.Quiz(
            title=title,
            subject=subject,
            language=language,
            provenance="Jeu de démonstration NextStep Maroc",
            validation_status=m.VERIFICATION_DEMO,
        )
        session.add(quiz)
        session.flush()
        specs = questions or [
            {
                "statement": "Question de test 1",
                "options": ["Bonne réponse", "Mauvaise réponse"],
                "correct_index": 0,
                "explanation": "Explication 1",
            },
            {
                "statement": "Question de test 2",
                "options": ["Option A", "Bonne réponse"],
                "correct_index": 1,
                "explanation": "Explication 2",
            },
        ]
        for position, spec in enumerate(specs, start=1):
            question = m.QuizQuestion(
                quiz_id=quiz.id,
                statement=spec["statement"],
                explanation=spec.get("explanation"),
                language=language,
                position=position,
                provenance="Jeu de démonstration NextStep Maroc",
                validation_status=m.VERIFICATION_DEMO,
            )
            session.add(question)
            session.flush()
            for option_position, text in enumerate(spec["options"], start=1):
                session.add(
                    m.QuizOption(
                        question_id=question.id,
                        text=text,
                        is_correct=(option_position - 1) == spec.get("correct_index", 0),
                        position=option_position,
                    )
                )
        session.flush()
        return quiz

    return _make


@pytest.fixture()
def catalog(session, make_school, make_program, make_rule):
    """Mini-catalogue de test : deux écoles, trois formations, critères variés."""
    encg = make_school("ENCG de test", city="Casablanca", domain="gestion")
    ensi = make_school("ENS de test", city="Rabat", domain="informatique")

    gestion = make_program(encg, "Mastère en gestion", degree_level="mastère", domain="gestion")
    finance = make_program(
        encg,
        "Licence en finance",
        degree_level="licence",
        domain="finance",
        tuition_fees_mad=None,  # information non connue → jamais inventée
    )
    info = make_program(ensi, "Ingénieur informatique", degree_level="ingénieur", domain="informatique")

    make_rule(
        gestion,
        [
            {"criterion_type": "bac_series", "value": ["Économie et Gestion", "SVT"]},
            {"criterion_type": "min_average", "value": 12.0},
        ],
    )
    make_rule(
        finance,
        [{"criterion_type": "bac_series", "value": ["Économie et Gestion"]}],
        status=m.VERIFICATION_PENDING,
        label="Critères non vérifiés",
    )
    return {"encg": encg, "ensi": ensi, "gestion": gestion, "finance": finance, "info": info}
