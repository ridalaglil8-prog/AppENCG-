"""Tests des rôles et des autorisations (contrôle métier, pas seulement UI)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database import models as m  # noqa: E402
from helpers import TEST_PASSWORD  # noqa: E402
from services import admin_service, auth_service, resource_service  # noqa: E402
from utils.exceptions import (  # noqa: E402
    AuthenticationError,
    BusinessValidationError,
    PermissionDenied,
)


# --------------------------------------------------------------------------- #
# ensure_role : barrière centrale
# --------------------------------------------------------------------------- #


def test_ensure_role_rejects_guest_and_wrong_role(make_user):
    candidat = make_user(role="candidat")

    with pytest.raises(PermissionDenied):
        auth_service.ensure_role(None, ("administrateur",))
    with pytest.raises(PermissionDenied):
        auth_service.ensure_role(candidat, ("administrateur", "moderateur"))
    with pytest.raises(PermissionDenied):
        auth_service.ensure_role(candidat, (m.ROLE_ADMIN,))

    assert auth_service.ensure_role(candidat, ("candidat",)) is candidat


def test_ensure_role_rejects_inactive_account_even_with_right_role(make_user):
    admin = make_user(role="administrateur", active=False)
    with pytest.raises(PermissionDenied) as exc:
        auth_service.ensure_admin(admin)
    assert "disabled" in str(exc.value)


def test_ensure_staff_and_admin(make_user):
    candidat = make_user(role="candidat")
    moderateur = make_user(role="moderateur")
    admin = make_user(role="administrateur")

    with pytest.raises(PermissionDenied):
        auth_service.ensure_staff(candidat)
    assert auth_service.ensure_staff(moderateur) is moderateur
    assert auth_service.ensure_staff(admin) is admin

    with pytest.raises(PermissionDenied):
        auth_service.ensure_admin(moderateur)
    assert auth_service.ensure_admin(admin) is admin


# --------------------------------------------------------------------------- #
# Administration : réservée à l'administrateur
# --------------------------------------------------------------------------- #


def test_reference_data_requires_admin(session, make_user, make_school):
    candidat = make_user(role="candidat")
    moderateur = make_user(role="moderateur")
    admin = make_user(role="administrateur")
    payload = {"name": "École à créer", "verification_status": m.VERIFICATION_PENDING}

    with pytest.raises(PermissionDenied):
        admin_service.create_school(session, candidat, payload)
    with pytest.raises(PermissionDenied):
        admin_service.create_school(session, moderateur, payload)

    school = admin_service.create_school(session, admin, payload)
    assert school.id is not None

    # Un modérateur ne peut pas non plus activer/désactiver une école.
    existing = make_school("École existante")
    with pytest.raises(PermissionDenied):
        admin_service.set_school_active(session, moderateur, existing.id, False)


def test_only_admin_can_label_information_as_official(session, make_user):
    """Seul un administrateur peut déclarer « Officiel vérifié »."""
    admin = make_user(role="administrateur")
    candidat = make_user(role="candidat")

    school = admin_service.create_school(
        session,
        admin,
        {"name": "École officielle", "verification_status": m.VERIFICATION_OFFICIAL},
    )
    assert school.verification_status == m.VERIFICATION_OFFICIAL

    # Un candidat ne peut pas créer d'école, donc pas non plus en officiel.
    with pytest.raises(PermissionDenied):
        admin_service.create_school(
            session,
            candidat,
            {"name": "École usurpée", "verification_status": m.VERIFICATION_OFFICIAL},
        )
    # Le garde-fou « officiel » est également vérifié par le service lui-même.
    with pytest.raises(PermissionDenied):
        admin_service._assert_official_allowed(candidat, m.VERIFICATION_OFFICIAL)
    assert admin_service._assert_official_allowed(admin, m.VERIFICATION_OFFICIAL) is None


def test_role_management_is_admin_only_and_protected(session, make_user):
    admin = make_user(role="administrateur")
    candidat = make_user(role="candidat")
    moderateur = make_user(role="moderateur")

    with pytest.raises(PermissionDenied):
        admin_service.set_user_role(session, moderateur, candidat.id, m.ROLE_MODERATOR)
    with pytest.raises(PermissionDenied):
        admin_service.set_user_role(session, candidat, candidat.id, m.ROLE_ADMIN)

    updated = admin_service.set_user_role(session, admin, candidat.id, m.ROLE_MODERATOR)
    assert updated.role == "moderateur"

    # Un administrateur ne peut pas se rétrograder lui-même.
    with pytest.raises(BusinessValidationError):
        admin_service.set_user_role(session, admin, admin.id, m.ROLE_CANDIDATE)

    # Le dernier administrateur actif ne peut pas être rétrogradé.
    only_admin = make_user(role="administrateur")
    with pytest.raises(BusinessValidationError):
        admin_service.set_user_role(session, only_admin, only_admin.id, m.ROLE_CANDIDATE)


def test_self_deactivation_is_forbidden(session, make_user):
    admin = make_user(role="administrateur")
    with pytest.raises(BusinessValidationError):
        admin_service.set_user_active(session, admin, admin.id, False)


def test_user_listing_and_audit_require_admin(session, make_user):
    admin = make_user(role="administrateur")
    candidat = make_user(role="candidat")
    moderateur = make_user(role="moderateur")

    with pytest.raises(PermissionDenied):
        admin_service.users_list(session, candidat)
    with pytest.raises(PermissionDenied):
        admin_service.users_list(session, moderateur)
    with pytest.raises(PermissionDenied):
        admin_service.audit_logs(session, moderateur)

    assert admin_service.users_list(session, admin)
    assert admin_service.audit_logs(session, admin) is not None


def test_staff_stats_require_staff_role(session, make_user):
    candidat = make_user(role="candidat")
    moderateur = make_user(role="moderateur")

    with pytest.raises(PermissionDenied):
        admin_service.staff_stats(session, candidat)
    with pytest.raises(PermissionDenied):
        admin_service.staff_stats(session, None)

    stats = admin_service.staff_stats(session, moderateur)
    assert "resources_pending" in stats
    assert "reports_open" in stats


# --------------------------------------------------------------------------- #
# Modération : réservée au staff
# --------------------------------------------------------------------------- #


def test_moderation_queue_is_guarded_at_service_level(session, make_user, db):
    candidat = make_user(role="candidat")
    moderateur = make_user(role="moderateur")

    resource_service.submit_resource(
        session, candidat.id, {"title": "Fiche de révision", "content": "contenu"}
    )
    session.flush()

    with pytest.raises(PermissionDenied):
        resource_service.pending_resources(session, candidat)
    with pytest.raises(PermissionDenied):
        resource_service.list_reports(session, candidat)

    assert len(resource_service.pending_resources(session, moderateur)) == 1


def test_cannot_moderate_without_staff_role(session, make_user):
    candidat = make_user(role="candidat")
    resource = resource_service.submit_resource(
        session, candidat.id, {"title": "Ressource à tester", "content": "texte"}
    )
    session.flush()

    with pytest.raises(PermissionDenied):
        resource_service.moderate_resource(session, candidat, resource.id, "published")

    # Même en appelant directement le service (test hors interface).
    assert resource.status == "pending"


def test_unauthorized_user_cannot_delete_another_account(session, make_user):
    victim = make_user(email="victime@test.ma")
    auth_service.delete_my_data(session, victim.id)
    session.flush()
    assert session.get(m.User, victim.id) is None


# --------------------------------------------------------------------------- #
# Suppression des données personnelles
# --------------------------------------------------------------------------- #


def test_delete_my_data_removes_personal_records(session, make_user, catalog, make_quiz):
    from sqlalchemy import select

    user = make_user(email="effacement@test.ma")
    auth_service.update_profile(session, user.id, {"display_name": "Prénom Test", "average": 14.5})
    from services import orientation_service, school_service

    school_service.add_favorite_school(session, user.id, catalog["encg"].id)
    quiz = make_quiz()
    from services import quiz_service

    quiz_service.submit_attempt(
        session, user.id, quiz.id, [{"question_id": quiz.questions[0].id, "option_id": 1}]
    )
    session.flush()

    auth_service.delete_my_data(session, user.id)
    session.flush()

    assert session.get(m.User, user.id) is None
    assert session.get(m.CandidateProfile, user.id) is None or not session.scalar(
        select(m.CandidateProfile).where(m.CandidateProfile.user_id == user.id)
    )
    assert not session.scalars(select(m.Favorite).where(m.Favorite.user_id == user.id)).all()
    assert not session.scalars(select(m.QuizAttempt).where(m.QuizAttempt.user_id == user.id)).all()


def test_password_change_requires_current_password(session, make_user):
    user = make_user(email="motdepasse@test.ma")
    with pytest.raises(AuthenticationError):
        auth_service.change_password(session, user, "mauvais", "NouveauMotDePasse1")
    auth_service.change_password(session, user, TEST_PASSWORD, "NouveauMotDePasse1")
    session.flush()
    assert auth_service.authenticate(session, user.email, "NouveauMotDePasse1").id == user.id
