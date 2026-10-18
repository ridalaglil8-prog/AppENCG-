"""Tests de validation du profil candidat (Pydantic + service)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pydantic import ValidationError  # noqa: E402

from services import auth_service  # noqa: E402
from utils.exceptions import BusinessValidationError  # noqa: E402
from utils.validators import ProfileInput, RegistrationInput  # noqa: E402


def test_valid_profile_is_accepted():
    payload = ProfileInput(
        display_name="Salma",
        bac_series="Économie et Gestion",
        bac_year=2026,
        city="Casablanca",
        average=14.25,
        favorite_subjects=["subj_accounting", "subj_math"],
        interests=["int_finance"],
        desired_fields=["Gestion"],
        geographic_preference="geo_big_city",
    )
    assert payload.average == 14.25
    assert payload.bac_series == "Économie et Gestion"


def test_average_out_of_range_is_rejected():
    with pytest.raises(ValidationError):
        ProfileInput(average=21)
    with pytest.raises(ValidationError):
        ProfileInput(average=-1)


def test_bac_year_bounds_are_enforced():
    with pytest.raises(ValidationError):
        ProfileInput(bac_year=1899)
    with pytest.raises(ValidationError):
        ProfileInput(bac_year=2101)


def test_markup_in_display_name_is_rejected():
    with pytest.raises(ValidationError):
        ProfileInput(display_name="<script>alert(1)</script>")


def test_list_fields_are_cleaned_and_deduplicated():
    payload = ProfileInput(favorite_subjects=[" subj_math ", "subj_math", "", "subj_physics"])
    assert payload.favorite_subjects == ["subj_math", "subj_physics"]


def test_too_many_list_items_are_rejected():
    with pytest.raises(ValidationError):
        ProfileInput(interests=[f"item-{index}" for index in range(31)])


def test_whitespace_only_fields_become_none():
    payload = ProfileInput(city="   ", display_name="  ")
    assert payload.city is None
    assert payload.display_name is None


def test_update_profile_raises_business_error_on_invalid_data(session, make_user):
    user = make_user()
    with pytest.raises(BusinessValidationError) as exc:
        auth_service.update_profile(session, user.id, {"average": 42})
    assert "error_validation" in str(exc.value)


def test_update_profile_creates_then_updates_single_row(session, make_user):
    """Le formulaire de profil remplace l'ensemble des champs (une seule ligne)."""
    user = make_user()
    first = auth_service.update_profile(
        session, user.id, {"display_name": "Amine", "average": 11, "city": "Rabat"}
    )
    session.flush()
    second = auth_service.update_profile(
        session, user.id, {"display_name": "Amine", "average": 12.5, "city": "Fès"}
    )
    session.flush()

    assert first.id == second.id
    assert second.average == 12.5
    assert second.city == "Fès"
    # Une ligne de profil par compte (contrainte d'unicité de user_id).
    from sqlalchemy import func, select

    count = session.scalar(
        select(func.count()).select_from(first.__class__).where(first.__class__.user_id == user.id)
    )
    assert count == 1


def test_profile_is_persisted_with_timestamps(session, make_user):
    user = make_user()
    profile = auth_service.update_profile(session, user.id, {"display_name": "Test"})
    session.flush()
    assert profile.created_at is not None
    assert profile.updated_at is not None


def test_registration_email_is_normalized():
    payload = RegistrationInput(email="  Moi@Example.MA ", password="MotDePasse1")
    assert payload.email == "moi@example.ma"
