"""Tests des ressources communautaires : modération obligatoire et signalements."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import select  # noqa: E402

from database import models as m  # noqa: E402
from services import resource_service  # noqa: E402
from utils.exceptions import BusinessValidationError, NotFoundError, PermissionDenied  # noqa: E402


def _submit(session, user_id, **overrides):
    payload = {
        "title": "Fiche de révision — Accounting",
        "description": "Résumé du programme",
        "category": "fiche",
        "language": "fr",
        "content": "Contenu de la fiche",
    }
    payload.update(overrides)
    return resource_service.submit_resource(session, user_id, payload)


# --------------------------------------------------------------------------- #
# Soumission
# --------------------------------------------------------------------------- #


def test_submitted_resource_is_pending_never_published(session, make_user):
    user = make_user()
    resource = _submit(session, user.id)
    session.flush()
    assert resource.status == "pending"
    assert resource.is_demo is False
    assert resource.submitted_by == user.id
    # Rien n'est publié automatiquement.
    assert resource_service.published_resources(session) == []


def test_pending_queue_contains_only_pending_items(session, make_user):
    user = make_user()
    _submit(session, user.id)
    session.flush()
    queue = resource_service.pending_resources(session, make_user(role="moderateur"))
    assert [r.status for r in queue] == ["pending"]


def test_resource_title_too_short_is_rejected(session, make_user):
    user = make_user()
    with pytest.raises(BusinessValidationError):
        _submit(session, user.id, title="OK")


def test_resource_language_must_be_supported(session, make_user):
    user = make_user()
    with pytest.raises(BusinessValidationError):
        _submit(session, user.id, language="de")


def test_submitter_must_be_a_known_account(session):
    with pytest.raises(PermissionDenied):
        resource_service.submit_resource(session, 999_999, {"title": "Ressource fantôme"})


# --------------------------------------------------------------------------- #
# Modération
# --------------------------------------------------------------------------- #


def test_full_moderation_lifecycle(session, make_user):
    author = make_user(email="auteur@test.ma")
    moderator = make_user(role="moderateur")
    resource = _submit(session, author.id)
    session.flush()

    resource_service.moderate_resource(session, moderator, resource.id, "to_revise", "préciser la source")
    assert resource.status == "to_revise"

    resource_service.moderate_resource(session, moderator, resource.id, "published")
    session.flush()
    assert resource.status == "published"
    assert [r.id for r in resource_service.published_resources(session)] == [resource.id]

    resource_service.moderate_resource(session, moderator, resource.id, "archived")
    session.flush()
    assert resource_service.published_resources(session) == []

    # Journal d'audit de la modération.
    actions = session.scalars(select(m.AuditLog.action)).all()
    assert "resource.moderated" in actions
    assert "resource.submitted" in actions


def test_invalid_status_is_rejected(session, make_user):
    author = make_user(email="auteur2@test.ma")
    moderator = make_user(role="moderateur")
    resource = _submit(session, author.id)
    session.flush()
    with pytest.raises(BusinessValidationError):
        resource_service.moderate_resource(session, moderator, resource.id, "invente")


def test_candidate_cannot_moderate(session, make_user):
    author = make_user(email="auteur3@test.ma")
    other = make_user(email="autre@test.ma")
    resource = _submit(session, author.id)
    session.flush()

    with pytest.raises(PermissionDenied):
        resource_service.moderate_resource(session, other, resource.id, "published")
    assert resource.status == "pending"


def test_rejection_records_reviewer(session, make_user):
    author = make_user(email="auteur4@test.ma")
    admin = make_user(role="administrateur")
    resource = _submit(session, author.id)
    session.flush()

    resource_service.moderate_resource(session, admin, resource.id, "rejected", "information non sourcée")
    session.flush()
    assert resource.status == "rejected"
    assert resource.reviewed_by == admin.id
    assert resource.review_note == "information non sourcée"


# --------------------------------------------------------------------------- #
# Signalements
# --------------------------------------------------------------------------- #


def test_report_flow(session, make_user):
    author = make_user(email="auteur5@test.ma")
    reporter = make_user(email="signaleur@test.ma")
    moderator = make_user(role="moderateur")
    resource = _submit(session, author.id)
    session.flush()

    report = resource_service.report_resource(session, reporter.id, resource.id, "contenu inapproprié")
    session.flush()
    assert report.status == "open"

    open_reports = resource_service.list_reports(session, moderator, status="open")
    assert len(open_reports) == 1
    assert open_reports[0].resource.id == resource.id

    resource_service.resolve_report(session, moderator, report.id, "resolved")
    session.flush()
    assert report.status == "resolved"
    assert report.resolved_by == moderator.id
    assert resource_service.list_reports(session, moderator, status="open") == []


def test_duplicate_report_from_same_user_is_rejected(session, make_user):
    author = make_user(email="auteur6@test.ma")
    reporter = make_user(email="double@test.ma")
    resource = _submit(session, author.id)
    session.flush()

    resource_service.report_resource(session, reporter.id, resource.id, "raison valide")
    session.flush()
    with pytest.raises(BusinessValidationError):
        resource_service.report_resource(session, reporter.id, resource.id, "raison valide encore")


def test_short_report_reason_is_rejected(session, make_user):
    author = make_user(email="auteur7@test.ma")
    reporter = make_user(email="court@test.ma")
    resource = _submit(session, author.id)
    session.flush()
    with pytest.raises(BusinessValidationError):
        resource_service.report_resource(session, reporter.id, resource.id, "ok")


def test_candidate_cannot_resolve_report(session, make_user):
    author = make_user(email="auteur8@test.ma")
    reporter = make_user(email="signaleur2@test.ma")
    candidat = make_user(email="candidat3@test.ma")
    resource = _submit(session, author.id)
    session.flush()
    report = resource_service.report_resource(session, reporter.id, resource.id, "signalement valide")
    session.flush()

    with pytest.raises(PermissionDenied):
        resource_service.resolve_report(session, candidat, report.id, "dismissed")
    assert report.status == "open"


def test_report_on_unknown_resource_raises(session, make_user):
    user = make_user()
    with pytest.raises(NotFoundError):
        resource_service.report_resource(session, user.id, 123_456, "raison suffisante")


def test_invalid_report_status_is_rejected(session, make_user):
    author = make_user(email="auteur9@test.ma")
    reporter = make_user(email="signaleur3@test.ma")
    moderator = make_user(role="moderateur")
    resource = _submit(session, author.id)
    session.flush()
    report = resource_service.report_resource(session, reporter.id, resource.id, "raison valide")
    session.flush()
    with pytest.raises(BusinessValidationError):
        resource_service.resolve_report(session, moderator, report.id, "n_importe_quoi")


def test_status_counts_cover_every_status(session, make_user):
    user = make_user()
    _submit(session, user.id)
    session.flush()
    counts = resource_service.resource_status_counts(session)
    assert set(counts) == set(resource_service.RESOURCE_STATUS_VALUES)
    assert counts["pending"] == 1
