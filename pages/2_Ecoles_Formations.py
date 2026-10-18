"""Page — Catalogue des écoles et formations.

Recherche et filtres (ville, domaine, type de diplôme, série du bac admissible)
appliqués par ``services.school_service``. Les filtres reposent sur des valeurs
issues de la base : aucune option n'est inventée côté interface.
"""

from __future__ import annotations

import streamlit as st

from components.cards import deadline_card, program_card, school_card
from components.layout import badge, footer, h, heading, html_block, notice, section_heading, unknown
from components.navigation import (
    current_language,
    current_user,
    flash_messages,
    prepare_page,
    set_flash,
)
from database import repositories as repo
from database.connection import db_session, get_database
from services import school_service
from utils.translations import tr

lang = prepare_page()
flash_messages(lang)
user = current_user()


@st.cache_data(ttl=60, show_spinner=False)
def _facets(database_url: str) -> dict:
    with db_session() as session:
        return school_service.catalog_facets(session)


def _toggle_favorite(target_type: str, target_id: int, is_fav: bool) -> None:
    if user is None:
        st.info(tr("ori_login_required", lang))
        return
    with db_session() as session:
        if target_type == "school":
            if is_fav:
                school_service.remove_favorite_school(session, user.id, target_id)
            else:
                school_service.add_favorite_school(session, user.id, target_id)
        else:
            if is_fav:
                school_service.remove_favorite_program(session, user.id, target_id)
            else:
                school_service.add_favorite_program(session, user.id, target_id)
    set_flash("msg_fav_removed" if is_fav else "msg_fav_added")
    st.rerun()


# --------------------------------------------------------------------------- #
# Filtres (barre latérale)
# --------------------------------------------------------------------------- #


def _filters() -> dict:
    st.sidebar.markdown(f"**{tr('btn_search', lang)}**")
    facets = _facets(get_database().url)
    filters = {}
    filters["name"] = st.sidebar.text_input(tr("sch_search", lang), key="f_school_name")
    filters["city"] = st.sidebar.selectbox(
        tr("sch_filter_city", lang),
        options=[""] + facets["cities"],
        format_func=lambda v: v if v else tr("sch_all", lang),
        key="f_city",
    )
    filters["domain"] = st.sidebar.selectbox(
        tr("sch_filter_domain", lang),
        options=[""] + facets["domains"],
        format_func=lambda v: v if v else tr("sch_all", lang),
        key="f_domain",
    )
    filters["school_type"] = st.sidebar.selectbox(
        tr("sch_filter_type", lang),
        options=[""] + facets["school_types"],
        format_func=lambda v: v if v else tr("sch_all", lang),
        key="f_type",
    )
    filters["degree"] = st.sidebar.selectbox(
        tr("sch_filter_degree", lang),
        options=[""] + facets["degrees"],
        format_func=lambda v: v if v else tr("sch_all", lang),
        key="f_degree",
    )
    if facets["series"]:
        filters["series"] = st.sidebar.selectbox(
            tr("sch_filter_series", lang),
            options=[""] + facets["series"],
            format_func=lambda v: v if v else tr("sch_all", lang),
            key="f_series",
        )
        st.sidebar.caption(tr("sch_series_filter_note", lang))
    else:
        filters["series"] = ""
        st.sidebar.caption(tr("common_unknown", lang))

    if st.sidebar.button(tr("btn_reset", lang), key="f_reset", use_container_width=True):
        for key in ("f_school_name", "f_city", "f_domain", "f_type", "f_degree", "f_series"):
            st.session_state.pop(key, None)
        st.session_state.pop("school_detail", None)
        st.rerun()
    return {k: v for k, v in filters.items() if v}


# --------------------------------------------------------------------------- #
# Vue fiche d'une école
# --------------------------------------------------------------------------- #


def _school_detail(school_id: int) -> None:
    with db_session() as session:
        try:
            school = school_service.get_school_detail(session, school_id)
        except Exception:
            st.error(tr("error_not_found", lang))
            st.session_state.pop("school_detail", None)
            return
        programs = school_service.list_programs(session, school.id)
        deadlines = [
            d for d in school_service.all_deadlines(session) if d.school_id == school.id
        ]
        program_deadlines = [
            d for d in school_service.all_deadlines(session) if d.program_id in {p.id for p in programs}
        ]
        is_fav = school_service.is_favorite(session, user.id if user else None, "school", school.id)
        program_favs = {
            p.id: school_service.is_favorite(session, user.id if user else None, "program", p.id)
            for p in programs
        }

    if st.button(f"← {tr('sch_back_list', lang)}", key="back_to_list"):
        st.session_state.pop("school_detail", None)
        st.rerun()

    html_block(f'<div class="ns-title">{h(school.name)}</div>')
    meta = " · ".join(x for x in [school.city, school.domain, school.school_type] if x)
    if meta:
        html_block(f'<div class="ns-subtitle">{h(meta)}</div>')
    html_block(badge(lang, school.verification_status))
    if school.last_verified_at:
        st.caption(
            f"{tr('common_last_verified', lang)} : {school.last_verified_at.isoformat()}"
        )

    if school.description:
        st.write(school.description)
    if school.official_url:
        st.markdown(f"[{tr('common_official_url', lang)} →]({school.official_url})")
    else:
        st.caption(unknown(lang))

    if school.verification_status == "demo":
        notice("demo", tr("sch_demo_banner", lang))
    elif not school.official_url:
        notice("warn", tr("common_unknown", lang))

    fav_clicked = school_card(
        lang,
        school,
        favorite=is_fav,
        fav_key=f"fav_school_detail_{school.id}",
        show_program_count=0,
    )
    if fav_clicked:
        _toggle_favorite("school", school.id, is_fav)

    section_heading(lang, tr("sch_programs", lang))
    if not programs:
        st.info(tr("sch_no_result", lang))
    for program in programs:
        clicked = program_card(
            lang,
            program,
            favorite=program_favs.get(program.id, False),
            fav_key=f"fav_program_{program.id}",
            show_admission=True,
        )
        if clicked:
            _toggle_favorite("program", program.id, program_favs.get(program.id, False))

    section_heading(lang, tr("sch_deadlines", lang))
    combined = deadlines + program_deadlines
    if not combined:
        st.info(tr("sch_no_deadline", lang))
    for deadline in combined:
        deadline_card(lang, deadline, context_label=school.name)


# --------------------------------------------------------------------------- #
# Vue liste
# --------------------------------------------------------------------------- #


def _school_list(filters: dict) -> None:
    with db_session() as session:
        schools = school_service.search_catalog(session, **filters)
        fav_ids = school_service.favorite_school_ids(session, user.id if user else None)

    st.caption(tr("sch_results", lang, count=len(schools)))
    if not schools:
        st.info(tr("sch_no_result", lang))
        return

    for row_start in range(0, len(schools), 2):
        cols = st.columns(2)
        for col, school in zip(cols, schools[row_start : row_start + 2]):
            with col:
                fav = school.id in fav_ids
                clicked = school_card(
                    lang,
                    school,
                    favorite=fav,
                    fav_key=f"fav_school_{school.id}",
                    show_program_count=2,
                )
                if clicked:
                    _toggle_favorite("school", school.id, fav)
                if st.button(
                    tr("btn_details", lang), key=f"open_school_{school.id}", use_container_width=True
                ):
                    st.session_state["school_detail"] = school.id
                    st.rerun()


heading(
    lang,
    tr("sch_title", lang),
    subtitle=tr("sch_intro", lang),
    kicker=tr("nav_schools", lang),
)
filters = _filters()
if st.session_state.get("school_detail"):
    _school_detail(int(st.session_state["school_detail"]))
else:
    _school_list(filters)
footer(lang)
