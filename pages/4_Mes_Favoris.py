"""Page — Mes favoris et échéances.

Deux zones : les écoles/formations enregistrées (ajout depuis le catalogue) et
les échéances, séparées en **confirmées** (source vérifiée + date renseignée)
et **non vérifiées**. Aucune notification n'est envoyée (rappels visuels seuls).
"""

from __future__ import annotations

import streamlit as st

from components.cards import deadline_card, program_card, school_card
from components.layout import footer, heading, notice, section_heading, unknown
from components.navigation import (
    current_language,
    current_user,
    flash_messages,
    prepare_page,
    set_flash,
)
from database.connection import db_session
from services import school_service
from utils.translations import tr

lang = prepare_page()
flash_messages(lang)
user = current_user()


heading(
    lang,
    tr("fav_title", lang),
    subtitle=tr("fav_intro", lang),
    kicker=tr("nav_favorites", lang),
)

if user is None:
    st.info(tr("dash_login_required", lang))
    st.page_link("pages/5_Mon_Profil.py", label=tr("btn_login", lang), icon="👤")
else:
    with db_session() as session:
        favorites = school_service.list_favorites(session, user.id)

    schools = [f for f in favorites if f.target_type == "school" and f.school]
    programs = [f for f in favorites if f.target_type == "program" and f.program]

    col_schools, col_programs = st.columns(2)

    with col_schools:
        section_heading(lang, tr("fav_schools", lang))
        if not schools:
            st.info(tr("fav_empty", lang))
        for fav in schools:
            if st.button(
                f"✕ {tr('btn_remove_fav', lang)} — {fav.school.name}",
                key=f"unfav_school_{fav.id}",
                use_container_width=True,
            ):
                with db_session() as session:
                    school_service.remove_favorite_school(session, user.id, fav.school_id)
                set_flash("msg_fav_removed")
                st.rerun()
            if st.button(
                tr("btn_details", lang), key=f"fav_open_{fav.school_id}", use_container_width=True
            ):
                st.session_state["school_detail"] = fav.school_id
                st.switch_page("pages/2_Ecoles_Formations.py")

    with col_programs:
        section_heading(lang, tr("fav_programs", lang))
        if not programs:
            st.info(tr("fav_empty", lang))
        for fav in programs:
            clicked = program_card(
                lang,
                fav.program,
                favorite=True,
                fav_key=f"unfav_program_{fav.id}",
            )
            if clicked:
                with db_session() as session:
                    school_service.remove_favorite_program(session, user.id, fav.program_id)
                set_flash("msg_fav_removed")
                st.rerun()

    # ----------------------------------------------------------------- #
    # Échéances
    # ----------------------------------------------------------------- #
    section_heading(lang, tr("dl_title", lang), tr("dl_reminder_note", lang))

    with db_session() as session:
        confirmed = school_service.confirmed_deadlines(session)
        unverified = school_service.unverified_deadlines(session)

    st.markdown(f"**{tr('dl_confirmed', lang)}**")
    if not confirmed:
        st.info(tr("dl_none_confirmed", lang))
    for deadline in confirmed:
        context = (
            deadline.school.name
            if deadline.school
            else (deadline.program.name if deadline.program else "")
        )
        deadline_card(lang, deadline, context_label=context)

    st.markdown(f"**{tr('dl_unconfirmed', lang)}**")
    if not unverified:
        st.caption(tr("common_none", lang))
    for deadline in unverified:
        context = (
            deadline.school.name
            if deadline.school
            else (deadline.program.name if deadline.program else "")
        )
        deadline_card(lang, deadline, context_label=context)

    notice("info", tr("dl_reminder_note", lang))

footer(lang)
