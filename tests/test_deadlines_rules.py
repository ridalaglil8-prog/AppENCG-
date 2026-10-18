"""Tests des échéances : dates inconnues, sources, contrôles administrateur."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database import models as m  # noqa: E402
from services import admin_service, school_service  # noqa: E402
from utils.exceptions import BusinessValidationError, PermissionDenied  # noqa: E402


def test_deadline_requires_a_target(session, make_user, catalog):
    admin = make_user(role="administrateur")
    with pytest.raises(BusinessValidationError):
        admin_service.add_deadline(
            session,
            admin,
            {"title": "Échéance sans cible", "deadline_type": "candidature"},
        )


def test_deadline_without_date_is_allowed_and_not_invented(session, make_user, catalog):
    admin = make_user(role="administrateur")
    deadline = admin_service.add_deadline(
        session,
        admin,
        {
            "title": "Date de concours à confirmer",
            "deadline_type": "concours",
            "school_id": catalog["encg"].id,
            "verification_status": m.VERIFICATION_PENDING,
        },
    )
    session.flush()
    assert deadline.event_date is None  # jamais de date fabriquée

    # Une échéance sans date n'est pas « confirmée ».
    confirmed = school_service.confirmed_deadlines(session)
    assert deadline not in confirmed
    assert any(row.id == deadline.id for row in school_service.unverified_deadlines(session))


def test_deadline_with_date_is_confirmed_only_when_official(session, make_user, catalog):
    admin = make_user(role="administrateur")
    deadline = admin_service.add_deadline(
        session,
        admin,
        {
            "title": "Dépôt des candidatures",
            "deadline_type": "candidature",
            "event_date": "2027-03-15",
            "school_id": catalog["encg"].id,
            "source_name": "Site officiel de l'école",
            "verification_status": m.VERIFICATION_OFFICIAL,
        },
    )
    session.flush()
    assert deadline.event_date.isoformat() == "2027-03-15"
    assert any(row.id == deadline.id for row in school_service.confirmed_deadlines(session))
    assert not any(row.id == deadline.id for row in school_service.unverified_deadlines(session))


def test_official_deadline_requires_source(session, make_user, catalog):
    admin = make_user(role="administrateur")
    with pytest.raises(BusinessValidationError):
        admin_service.add_deadline(
            session,
            admin,
            {
                "title": "Résultats",
                "deadline_type": "resultat",
                "event_date": "2027-05-01",
                "school_id": catalog["encg"].id,
                "verification_status": m.VERIFICATION_OFFICIAL,
            },
        )


def test_invalid_date_format_is_rejected(session, make_user, catalog):
    admin = make_user(role="administrateur")
    with pytest.raises(BusinessValidationError):
        admin_service.add_deadline(
            session,
            admin,
            {
                "title": "Date bancale",
                "deadline_type": "autre",
                "event_date": "15/03/2027",
                "school_id": catalog["encg"].id,
            },
        )


def test_deadline_creation_is_admin_only(session, make_user, catalog):
    candidat = make_user(role="candidat")
    with pytest.raises(PermissionDenied):
        admin_service.add_deadline(
            session,
            candidat,
            {
                "title": "Tentative",
                "deadline_type": "autre",
                "school_id": catalog["encg"].id,
            },
        )


def test_deadline_for_unknown_school_raises(session, make_user):
    admin = make_user(role="administrateur")
    from utils.exceptions import NotFoundError

    with pytest.raises(NotFoundError):
        admin_service.add_deadline(
            session,
            admin,
            {"title": "Cible absente", "deadline_type": "autre", "school_id": 424_242},
        )


def test_admission_rule_criteria_are_persisted(session, make_user, catalog):
    admin = make_user(role="administrateur")
    rule = admin_service.add_admission_rule(
        session,
        admin,
        {
            "program_id": catalog["info"].id,
            "label": "Critères officiels de test",
            "source_name": "Arrêté de test",
            "verification_status": m.VERIFICATION_OFFICIAL,
            "criteria": [
                {
                    "criterion_type": "bac_series",
                    "value": ["SVT", "PC"],
                    "operator": "in",
                    "is_required": True,
                    "verification_status": m.VERIFICATION_OFFICIAL,
                },
                {
                    "criterion_type": "min_average",
                    "value": 13.5,
                    "operator": "gte",
                    "is_required": False,
                    "verification_status": m.VERIFICATION_OFFICIAL,
                },
            ],
        },
    )
    session.flush()
    assert len(rule.criteria) == 2

    from services import orientation_service

    evaluation = orientation_service.evaluate_program(
        catalog["info"], {"bac_series": "SVT", "average": 14}
    )
    assert evaluation["status"] == orientation_service.STATUS_OK

    evaluation_ko = orientation_service.evaluate_program(
        catalog["info"], {"bac_series": "SVT", "average": 12}
    )
    # Critère de moyenne non obligatoire non satisfait : « vérification
    # nécessaire », jamais un « ko » qui serait une fausse conclusion.
    assert evaluation_ko["status"] == orientation_service.STATUS_UNKNOWN


def test_invalid_criterion_type_is_rejected(session, make_user, catalog):
    admin = make_user(role="administrateur")
    with pytest.raises(BusinessValidationError):
        admin_service.add_admission_rule(
            session,
            admin,
            {
                "program_id": catalog["info"].id,
                "criteria": [{"criterion_type": "magique", "value": 1}],
            },
        )
