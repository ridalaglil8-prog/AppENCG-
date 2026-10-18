"""Tests du catalogue : recherche, filtres, favoris, informations inconnues."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database import models as m  # noqa: E402
from database import repositories as repo  # noqa: E402
from services import school_service  # noqa: E402
from utils.helpers import verification_meta  # noqa: E402
from utils.translations import tr  # noqa: E402


# --------------------------------------------------------------------------- #
# Recherche et filtres
# --------------------------------------------------------------------------- #


def test_search_without_filter_returns_active_schools(session, catalog):
    names = [school.name for school in school_service.search_catalog(session)]
    assert "ENCG de test" in names
    assert "ENS de test" in names


def test_search_by_name_is_case_insensitive(session, catalog):
    results = school_service.search_catalog(session, name="encg")
    assert [s.name for s in results] == ["ENCG de test"]


def test_search_by_city_and_domain(session, catalog):
    assert [s.name for s in school_service.search_catalog(session, city="Rabat")] == ["ENS de test"]
    assert [s.name for s in school_service.search_catalog(session, domain="gestion")] == [
        "ENCG de test"
    ]
    assert school_service.search_catalog(session, city="Agadir") == []


def test_search_by_degree_returns_only_matching_schools(session, catalog):
    results = school_service.search_catalog(session, degree="ingénieur")
    assert [s.name for s in results] == ["ENS de test"]


def test_search_excludes_inactive_schools(session, catalog, make_school):
    hidden = make_school("École fermée", is_active=False)
    names = [s.name for s in school_service.search_catalog(session)]
    assert hidden.name not in names


def test_search_by_degree_then_filtered_school_keeps_matching_program_only(session, catalog):
    results = school_service.search_catalog(session, degree="licence")
    assert [s.name for s in results] == ["ENCG de test"]
    assert [p.name for p in results[0].programs] == ["Licence en finance"]


def test_series_filter_only_uses_official_rules(session, catalog):
    """Le filtre par série ne s'appuie que sur des critères officiellement vérifiés."""
    matched = school_service.search_catalog(session, series="Économie et Gestion")
    assert [s.name for s in matched] == ["ENCG de test"]  # règles officielles uniquement

    # La licence (règle « pending_verification ») n'apparaît donc pas pour une
    # série qui n'aurait aucune règle officielle.
    without_official_rule = school_service.search_catalog(session, series="Techniques Physiques")
    assert without_official_rule == []


def test_series_filter_returns_empty_when_no_official_rule(session, make_school, make_program, make_rule):
    school = make_school("École sans règle officielle")
    program = make_program(school, "Formation")
    make_rule(program, [{"criterion_type": "bac_series", "value": ["SVT"]}], status=m.VERIFICATION_PENDING)
    assert school_service.search_catalog(session, series="SVT") == []


def test_facets_are_derived_from_data(session, catalog):
    facets = school_service.catalog_facets(session)
    assert "Casablanca" in facets["cities"]
    assert "gestion" in facets["domains"]
    assert "mastère" in facets["degrees"]


def test_school_detail_raises_on_unknown_id(session):
    from utils.exceptions import NotFoundError

    with pytest.raises(NotFoundError):
        school_service.get_school_detail(session, 424242)


# --------------------------------------------------------------------------- #
# Informations non connues : jamais inventées
# --------------------------------------------------------------------------- #


def test_unknown_tuition_is_not_invented(session, catalog):
    finance = catalog["finance"]
    assert finance.tuition_fees_mad is None  # aucune valeur fabriquée


def test_unknown_verification_status_is_explicit(session, catalog):
    assert catalog["encg"].verification_status == m.VERIFICATION_PENDING
    meta = verification_meta(catalog["encg"].verification_status)
    assert meta["key"] == "status_pending"
    # Le libellé traduit existe dans les trois langues.
    for lang in ("fr", "ar", "en"):
        assert tr(meta["key"], lang)


def test_information_to_verify_label_is_available_in_three_languages():
    for lang in ("fr", "ar", "en"):
        label = tr("common_unknown", lang)
        assert label
        assert label != tr("common_unknown", "fr") or lang == "fr"


def test_program_without_rules_is_reported_as_no_rule(session, catalog):
    from services import orientation_service

    result = orientation_service.evaluate_program(catalog["info"], {"bac_series": "SVT", "average": 14})
    assert result["status"] == orientation_service.STATUS_NO_RULE
    assert result["checks"] == []


# --------------------------------------------------------------------------- #
# Favoris
# --------------------------------------------------------------------------- #


def test_favorite_school_add_list_and_remove(session, make_user, catalog):
    user = make_user()
    favorite = school_service.add_favorite_school(session, user.id, catalog["encg"].id)
    session.flush()
    assert favorite.target_type == m.FAV_SCHOOL

    assert catalog["encg"].id in school_service.favorite_school_ids(session, user.id)
    assert len(school_service.list_favorites(session, user.id)) == 1

    # Ajout en double : pas de doublon.
    school_service.add_favorite_school(session, user.id, catalog["encg"].id)
    session.flush()
    assert len(school_service.list_favorites(session, user.id)) == 1

    assert school_service.remove_favorite_school(session, user.id, catalog["encg"].id) is True
    session.flush()
    assert school_service.list_favorites(session, user.id) == []
    assert school_service.remove_favorite_school(session, user.id, catalog["encg"].id) is False


def test_favorite_program_roundtrip(session, make_user, catalog):
    user = make_user()
    school_service.add_favorite_program(session, user.id, catalog["gestion"].id)
    session.flush()
    assert school_service.is_favorite(session, user.id, "program", catalog["gestion"].id) is True
    counts = school_service.favorite_counts(session, user.id)
    assert counts["programs"] == 1
    assert counts["total"] == 1
    school_service.remove_favorite_program(session, user.id, catalog["gestion"].id)
    session.flush()
    assert school_service.is_favorite(session, user.id, "program", catalog["gestion"].id) is False


def test_favorites_of_guest_user_are_empty(session, catalog):
    assert school_service.favorite_school_ids(session, None) == set()
    assert school_service.is_favorite(session, None, "school", catalog["encg"].id) is False


def test_favorites_cannot_cross_users(session, make_user, catalog):
    alice = make_user(email="alice@test.ma")
    bob = make_user(email="bob@test.ma")
    school_service.add_favorite_school(session, alice.id, catalog["encg"].id)
    session.flush()
    assert catalog["encg"].id not in school_service.favorite_school_ids(session, bob.id)
