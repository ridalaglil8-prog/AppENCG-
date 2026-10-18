"""Page — Mon profil : connexion, inscription, profil candidat, données.

Sécurité rappelée dans l'interface : mots de passe hachés (bcrypt), collecte
minimale, suppression possible des données personnelles. ``st.session_state``
ne sert que d'état d'interface — les permissions sont vérifiées en base.
"""

from __future__ import annotations

import streamlit as st

from components.forms import login_form, profile_form, registration_form, show_service_error
from components.layout import badge, footer, h, heading, html_block, notice, section_heading, unknown
from components.navigation import (
    current_language,
    current_user,
    flash_messages,
    logout_user,
    prepare_page,
    set_flash,
)
from database import repositories as repo
from database.connection import db_session
from services import auth_service
from utils.exceptions import NextStepError
from utils.translations import LANGUAGES, tr

lang = prepare_page()
flash_messages(lang)
user = current_user()


def _account_panel() -> None:
    role_key = {
        "administrateur": "role_administrateur",
        "moderateur": "role_moderateur",
    }.get(user.role, "role_candidat")
    with st.container(border=True):
        c1, c2 = st.columns([3, 1])
        with c1:
            html_block(f"<div style='font-weight:700'>{h(user.email)}</div>")
            st.caption(
                f"{tr('label_language', lang)} : {LANGUAGES.get(user.language, user.language)}"
            )
        with c2:
            html_block(f"<span class='ns-badge ns-badge-com'>{h(tr(role_key, lang))}</span>")
        if st.button(tr("btn_logout", lang), key="profile_logout"):
            logout_user()
            set_flash("msg_logout_ok")
            st.rerun()


def _danger_zone() -> None:
    section_heading(lang, tr("btn_delete_my_data", lang))
    notice("warn", tr("profile_delete_confirm", lang))
    confirmed = st.checkbox(tr("common_yes", lang), key="confirm_delete_my_data")
    if st.button(tr("btn_delete_my_data", lang), key="delete_my_data_btn", disabled=not confirmed):
        try:
            with db_session() as session:
                auth_service.delete_my_data(session, user.id)
            logout_user()
            set_flash("profile_delete_done")
            st.rerun()
        except NextStepError as exc:
            show_service_error(lang, exc)


heading(
    lang,
    tr("profile_title", lang),
    subtitle=tr("profile_intro", lang),
    kicker=tr("nav_profile", lang),
)

if user is None:
    tab_login, tab_register = st.tabs(
        [tr("auth_login_title", lang), tr("auth_register_title", lang)]
    )
    with tab_login:
        st.caption(tr("auth_have_account", lang))
        login_form(lang)
    with tab_register:
        st.caption(tr("auth_no_account", lang))
        registration_form(lang)
    notice("info", tr("auth_privacy_note", lang))
    notice("warn", tr("profile_privacy_note", lang))
else:
    _account_panel()
    section_heading(lang, tr("profile_title", lang), tr("profile_intro", lang))
    with db_session() as session:
        profile = repo.get_profile(session, user.id)
    data = profile_form(lang, profile, user)
    if data is not None:
        try:
            with db_session() as session:
                auth_service.update_profile(session, user.id, data)
            set_flash("msg_saved")
            st.rerun()
        except NextStepError as exc:
            show_service_error(lang, exc)

    notice("info", tr("profile_privacy_note", lang))
    _danger_zone()

footer(lang)
