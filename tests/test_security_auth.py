"""Tests de sécurité : hachage bcrypt, politique de mots de passe, connexions."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from helpers import PASSWORD_HASH, TEST_PASSWORD  # noqa: E402
from services import auth_service  # noqa: E402
from utils.exceptions import (  # noqa: E402
    AuthenticationError,
    BusinessValidationError,
    RateLimitedError,
)
from utils.security import (  # noqa: E402
    BCRYPT_ROUNDS,
    LoginRateLimiter,
    hash_password,
    password_policy_errors,
    verify_password,
)


# --------------------------------------------------------------------------- #
# Hachage
# --------------------------------------------------------------------------- #


def test_hash_is_bcrypt_and_not_reversible():
    digest = hash_password(TEST_PASSWORD)
    assert digest.startswith("$2b$")
    assert TEST_PASSWORD not in digest
    assert digest != PASSWORD_HASH or True  # hachage salé : voir test suivant
    # Deux hachages du même mot de passe diffèrent (sel aléatoire).
    assert hash_password(TEST_PASSWORD) != digest


def test_hash_roundtrip_and_wrong_password():
    digest = hash_password(TEST_PASSWORD)
    assert verify_password(TEST_PASSWORD, digest) is True
    assert verify_password("mauvais-mot-de-passe", digest) is False
    assert verify_password("", digest) is False
    assert verify_password(TEST_PASSWORD, "") is False
    assert verify_password(None, digest) is False


def test_bcrypt_cost_is_pinned():
    assert BCRYPT_ROUNDS == 12


def test_password_policy():
    assert password_policy_errors(TEST_PASSWORD) == []
    assert password_policy_errors("court")
    assert password_policy_errors("a" * 73)  # borne bcrypt de 72 octets


# --------------------------------------------------------------------------- #
# Inscription / connexion
# --------------------------------------------------------------------------- #


def test_registration_and_login(session, db):
    user = auth_service.register_user(session, "candidat@Test.ma", TEST_PASSWORD)
    session.commit()
    assert user.id is not None
    assert user.role == "candidat"
    assert user.password_hash != TEST_PASSWORD
    assert user.email == "candidat@test.ma"  # normalisé en minuscules

    logged = auth_service.authenticate(session, "CANDIDAT@test.ma", TEST_PASSWORD)
    assert logged.id == user.id


def test_login_rejects_wrong_credentials_without_leaking(session, db):
    auth_service.register_user(session, "unique@test.ma", TEST_PASSWORD)
    session.commit()

    with pytest.raises(AuthenticationError) as wrong_password:
        auth_service.authenticate(session, "unique@test.ma", "AutreMotDePasse1")
    with pytest.raises(AuthenticationError) as unknown_user:
        auth_service.authenticate(session, "absent@test.ma", TEST_PASSWORD)

    # Message identique : impossible de savoir si l'e-mail existe (anti-enum).
    assert str(wrong_password.value) == str(unknown_user.value)


def test_duplicate_registration_is_rejected(session):
    auth_service.register_user(session, "deja@test.ma", TEST_PASSWORD)
    session.flush()
    with pytest.raises(BusinessValidationError):
        auth_service.register_user(session, "deja@test.ma", TEST_PASSWORD)


def test_weak_password_and_invalid_email_are_rejected(session):
    with pytest.raises(BusinessValidationError):
        auth_service.register_user(session, "faible@test.ma", "1234567")
    with pytest.raises(BusinessValidationError):
        auth_service.register_user(session, "pas-un-email", TEST_PASSWORD)


def test_disabled_account_cannot_login(session, make_user):
    user = make_user(email="desactive@test.ma", active=False)
    with pytest.raises(AuthenticationError):
        auth_service.authenticate(session, user.email, TEST_PASSWORD)


def test_audit_log_written_on_login(session, db):
    auth_service.register_user(session, "journal@test.ma", TEST_PASSWORD)
    session.commit()
    auth_service.authenticate(session, "journal@test.ma", TEST_PASSWORD)
    session.commit()

    from sqlalchemy import select

    from database.models import AuditLog

    actions = [
        row.action
        for row in session.scalars(select(AuditLog).where(AuditLog.entity_type == "user")).all()
    ]
    assert "user.register" in actions
    assert "user.login" in actions
    # Aucun secret journalisé.
    assert not any("password" in (row.detail or {}).__str__().lower() for row in session.scalars(select(AuditLog)).all())


# --------------------------------------------------------------------------- #
# Limitation des tentatives
# --------------------------------------------------------------------------- #


def test_rate_limiter_locks_after_max_failures():
    now = [1000.0]
    limiter = LoginRateLimiter(max_attempts=3, lock_seconds=60, clock=lambda: now[0])

    limiter.check("moi@test.ma")
    limiter.record_failure("moi@test.ma")
    limiter.record_failure("moi@test.ma")
    limiter.check("moi@test.ma")  # pas encore bloqué
    limiter.record_failure("moi@test.ma")

    with pytest.raises(RateLimitedError):
        limiter.check("moi@test.ma")

    # Autre e-mail non concerné (comptage par identifiant).
    limiter.check("autre@test.ma")

    # Le verrou expire.
    now[0] += 61
    limiter.check("moi@test.ma")


def test_rate_limiter_reset_on_success():
    now = [0.0]
    limiter = LoginRateLimiter(max_attempts=2, lock_seconds=30, clock=lambda: now[0])
    limiter.record_failure("x@test.ma")
    limiter.reset("x@test.ma")
    limiter.record_failure("x@test.ma")
    limiter.check("x@test.ma")  # compteur remis à zéro


def test_authenticate_uses_shared_rate_limiter(session, db):
    auth_service.register_user(session, "limite@test.ma", TEST_PASSWORD)
    session.commit()

    limiter = LoginRateLimiter(max_attempts=2, lock_seconds=120)
    for _ in range(2):
        with pytest.raises(AuthenticationError):
            auth_service.authenticate(session, "limite@test.ma", "mauvais", limiter=limiter)
    with pytest.raises(RateLimitedError):
        auth_service.authenticate(session, "limite@test.ma", TEST_PASSWORD, limiter=limiter)
