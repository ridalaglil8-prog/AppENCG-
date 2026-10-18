"""Formulaires réutilisables — inscription, connexion, profil candidat.

Les formulaires utilisent ``st.form`` : la soumission est explicite, les valeurs
ne sont pas réinitialisées à chaque rerun. Les erreurs affichées proviennent
des services (messages traduits), jamais de détails techniques.
"""

from __future__ import annotations

from typing import Any, Optional

import streamlit as st

from components.layout import h, html_block, notice
from components.navigation import login_user, set_flash
from database.models import CandidateProfile, User, utcnow
from services import auth_service
from services.auth_service import ensure_role  # noqa: F401 (ré-export pratique)
from utils.exceptions import (
    AuthenticationError,
    BusinessValidationError,
    NextStepError,
    PermissionDenied,
    RateLimitedError,
)
from utils.translations import tr
from utils.validators import KNOWN_BAC_SERIES, LANGUAGES

# Catalogues partagés avec le questionnaire d'orientation (clés stables).
SUBJECT_KEYS = [
    "subj_math", "subj_physics", "subj_svt", "subj_economics", "subj_accounting",
    "subj_languages", "subj_literature", "subj_it", "subj_law", "subj_history",
]
INTEREST_KEYS = [
    "int_manager", "int_finance", "int_marketing", "int_audit", "int_startup",
    "int_trade", "int_data", "int_teach", "int_law", "int_events",
]
FIELD_KEYS = [
    "pw_commerce", "pw_finance", "pw_marketing", "pw_audit", "pw_economie",
    "pw_entrepreneuriat", "pw_commerce_intl", "pw_data",
]


def show_service_error(lang: str, exc: Exception) -> None:
    """Traduit et affiche une erreur métier sans fuite de détail interne."""
    if isinstance(exc, RateLimitedError):
        st.error(tr("error_rate_limited", lang, seconds=exc.seconds))
    elif isinstance(exc, AuthenticationError):
        st.error(tr(str(exc), lang))
    elif isinstance(exc, PermissionDenied):
        st.error(tr(str(exc), lang))
    elif isinstance(exc, BusinessValidationError):
        details = " ".join(str(d) for d in getattr(exc, "details", [])[:3])
        st.error(tr(str(exc), lang) + (f" ({details})" if details else ""))
    elif isinstance(exc, NextStepError):
        st.error(tr(str(exc), lang))
    else:  # pragma: no cover - erreur inattendue : message générique seulement
        st.error(tr("error_generic", lang))


def login_form(lang: str) -> bool:
    """Formulaire de connexion. Retourne ``True`` si la connexion a réussi."""
    with st.form("login_form", clear_on_submit=False):
        email = st.text_input(tr("label_email", lang), key="login_email")
        password = st.text_input(
            tr("label_password", lang), type="password", key="login_password"
        )
        submitted = st.form_submit_button(tr("btn_login", lang), use_container_width=True)
    if not submitted:
        return False
    try:
        with _db() as session:
            user = auth_service.authenticate(session, email, password)
        login_user(user)
        set_flash("msg_login_ok")
        st.rerun()
        return True
    except NextStepError as exc:
        show_service_error(lang, exc)
        return False


def registration_form(lang: str) -> bool:
    """Formulaire d'inscription. Retourne ``True`` si le compte a été créé."""
    with st.form("register_form"):
        email = st.text_input(tr("label_email", lang), key="reg_email")
        password = st.text_input(
            f"{tr('label_password', lang)} — {tr('label_password_hint', lang)}",
            type="password",
            key="reg_password",
        )
        confirm = st.text_input(tr("label_password", lang) + " (2)", type="password", key="reg_confirm")
        language = st.selectbox(
            tr("label_language", lang),
            options=list(LANGUAGES),
            index=list(LANGUAGES).index(lang) if lang in LANGUAGES else 0,
            format_func=lambda code: LANGUAGES[code],
            key="reg_language",
        )
        notice("info", tr("auth_privacy_note", lang))
        submitted = st.form_submit_button(tr("btn_register", lang), use_container_width=True)
    if not submitted:
        return False
    if password != confirm:
        st.error(tr("error_validation", lang) + " : " + tr("label_password", lang))
        return False
    try:
        with _db() as session:
            user = auth_service.register_user(session, email, password, language)
        login_user(user)
        set_flash("msg_register_ok")
        st.rerun()
        return True
    except NextStepError as exc:
        show_service_error(lang, exc)
        return False


def profile_form(lang: str, profile: Optional[CandidateProfile], user: User) -> Optional[dict[str, Any]]:
    """Formulaire de profil pré-rempli. Retourne les données soumises ou ``None``."""
    profile = profile or None
    current_year = utcnow().year

    with st.form("profile_form"):
        display_name = st.text_input(
            tr("label_display_name", lang),
            value=(profile.display_name or "") if profile else "",
        )
        c1, c2 = st.columns(2)
        with c1:
            series_options = [""] + list(KNOWN_BAC_SERIES)
            current_series = (profile.bac_series if profile else None) or ""
            if current_series and current_series not in series_options:
                series_options.append(current_series)
            bac_series = st.selectbox(
                tr("label_bac_series", lang),
                options=series_options,
                index=series_options.index(current_series),
                format_func=lambda v: v if v else "—",
            )
        with c2:
            bac_year = st.number_input(
                tr("label_bac_year", lang),
                min_value=1990,
                max_value=current_year + 1,
                value=(profile.bac_year if profile and profile.bac_year else None),
                step=1,
            )
        c3, c4 = st.columns(2)
        with c3:
            city = st.text_input(
                tr("label_city", lang), value=(profile.city or "") if profile else ""
            )
        with c4:
            average = st.number_input(
                tr("label_average", lang),
                min_value=0.0,
                max_value=20.0,
                value=(profile.average if profile and profile.average is not None else None),
                step=0.25,
                format="%.2f",
            )

        favorite_subjects = st.multiselect(
            tr("label_favorite_subjects", lang),
            options=SUBJECT_KEYS,
            default=list(profile.favorite_subjects) if profile and profile.favorite_subjects else [],
            format_func=lambda key: tr(key, lang),
        )
        interests = st.multiselect(
            tr("label_interests", lang),
            options=INTEREST_KEYS,
            default=list(profile.interests) if profile and profile.interests else [],
            format_func=lambda key: tr(key, lang),
        )
        desired_fields = st.multiselect(
            tr("label_desired_fields", lang),
            options=FIELD_KEYS,
            default=list(profile.desired_fields) if profile and profile.desired_fields else [],
            format_func=lambda key: tr(key, lang),
        )
        geo_pref = st.text_input(
            tr("label_geo_pref", lang),
            value=(profile.geographic_preference or "") if profile else "",
        )
        budget_pref = st.text_input(
            tr("label_budget_pref", lang),
            value=(profile.budget_preference or "") if profile else "",
        )
        notice("info", tr("profile_intro", lang))
        submitted = st.form_submit_button(tr("btn_save", lang), use_container_width=True)

    if not submitted:
        return None
    return {
        "display_name": display_name,
        "bac_series": bac_series or None,
        "bac_year": int(bac_year) if bac_year else None,
        "city": city,
        "average": float(average) if average is not None else None,
        "favorite_subjects": favorite_subjects,
        "interests": interests,
        "desired_fields": desired_fields,
        "geographic_preference": geo_pref,
        "budget_preference": budget_pref,
    }


# --------------------------------------------------------------------------- #
# Helpers contexte DB (utilisés par les formulaires)
# --------------------------------------------------------------------------- #

from contextlib import contextmanager  # noqa: E402
from database.connection import get_database  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402


@contextmanager
def _db():
    """Session de travail propre aux formulaires (commit en sortie, rollback sur erreur)."""
    session: Session = get_database().session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


__all__ = [
    "FIELD_KEYS",
    "INTEREST_KEYS",
    "SUBJECT_KEYS",
    "login_form",
    "profile_form",
    "registration_form",
    "show_service_error",
]
