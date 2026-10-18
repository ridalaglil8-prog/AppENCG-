"""Tests du schéma : initialisation, idempotence, contraintes et index."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from sqlalchemy import func, inspect, select
from sqlalchemy.exc import IntegrityError

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database import connection, models as m  # noqa: E402
from helpers import PASSWORD_HASH  # noqa: E402

EXPECTED_TABLES = {
    "users",
    "candidate_profiles",
    "schools",
    "programs",
    "admission_rules",
    "admission_criteria",
    "deadlines",
    "quizzes",
    "quiz_questions",
    "quiz_options",
    "quiz_attempts",
    "orientation_results",
    "favorites",
    "resources",
    "reports",
    "audit_logs",
}


def test_schema_contains_every_mvp_table(db):
    tables = set(inspect(db.engine).get_table_names())
    missing = EXPECTED_TABLES - tables
    assert not missing, f"tables manquantes : {sorted(missing)}"


def test_init_is_idempotent_and_never_drops_data(db):
    """Ré-initialiser la base ne doit jamais écraser les données existantes."""
    with db.session() as session:
        user = m.User(email="persist@test.ma", password_hash=PASSWORD_HASH)
        session.add(user)
        session.flush()
        user_id = user.id

    connection.reset_database()
    connection.init_database(db.url)  # seconde initialisation du même fichier

    with db.session() as session:
        stored = session.get(m.User, user_id)
        assert stored is not None
        assert stored.email == "persist@test.ma"
        count = session.scalar(select(func.count()).select_from(m.User))
    assert count == 1


def test_foreign_keys_are_enforced(db):
    # 1) création d'une école (transaction fermée avant le test suivant).
    with db.session() as session:
        school = m.School(name="École FK", verification_status=m.VERIFICATION_PENDING)
        session.add(school)
        session.flush()
        school_id = school.id

    # 2) une formation pointant vers une école inexistante est refusée.
    with db.session() as session:
        session.add(m.Program(school_id=999_999, name="Orphelin"))
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()

    # 3) la même insertion avec une clé valide passe.
    with db.session() as session:
        session.add(m.Program(school_id=school_id, name="Fils valide"))
        session.flush()


def test_check_constraints_reject_unknown_role(db):
    with db.session() as session:
        session.add(m.User(email="bad-role@test.ma", password_hash=PASSWORD_HASH, role="superuser"))
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()


def test_unique_email_is_enforced(db):
    with db.session() as session:
        session.add(m.User(email="dup@test.ma", password_hash=PASSWORD_HASH))
        session.flush()
        session.add(m.User(email="dup@test.ma", password_hash=PASSWORD_HASH))
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()


def test_expected_indexes_exist(db):
    inspector = inspect(db.engine)
    indexes = {table: {ix["name"] for ix in inspector.get_indexes(table)} for table in EXPECTED_TABLES}

    assert "ix_users_role" in indexes["users"]
    assert "ix_schools_city_domain" in indexes["schools"]
    assert "ix_programs_domain_degree" in indexes["programs"]
    assert "ix_attempts_user_quiz" in indexes["quiz_attempts"]
    assert "ix_favorites_user_target" in indexes["favorites"]
    assert "ix_audit_action_created" in indexes["audit_logs"]


def test_timestamps_and_audit_columns(session, make_user):
    user = make_user()
    assert user.created_at is not None
    assert user.updated_at is not None

    session.add(
        m.AuditLog(actor_id=user.id, action="test.action", entity_type="user", entity_id=user.id)
    )
    session.flush()
    entry = session.scalar(select(m.AuditLog).order_by(m.AuditLog.id.desc()))
    assert entry.created_at is not None
    # Le journal ne contient aucun secret : ni mot de passe, ni hachage.
    assert "password" not in str(entry.detail or {}).lower()


def test_pragma_foreign_keys_enabled(db):
    with db.engine.connect() as connection_:
        value = connection_.exec_driver_sql("PRAGMA foreign_keys").scalar()
    assert int(value) == 1
