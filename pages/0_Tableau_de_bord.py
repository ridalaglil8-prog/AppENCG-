"""Page — Tableau de bord candidat.

Regroupe les données personnelles de l'utilisateur (profil, favoris, scores
QCM, résultat d'orientation, activités) et les éléments publics confirmés
(échéances vérifiées). Toutes les valeurs proviennent de la base ; rien n'est
simulé.
"""

from __future__ import annotations

import streamlit as st

from components.cards import deadline_card, match_card, pathway_card
from components.layout import (
    badge,
    footer,
    h,
    heading,
    html_block,
    notice,
    section_heading,
    stat_tile,
    unknown,
)
from components.navigation import (
    current_language,
    current_user,
    flash_messages,
    prepare_page,
)
from database import repositories as repo
from database.connection import db_session
from services import orientation_service as ori
from services import quiz_service, school_service
from utils.helpers import format_date, format_datetime, percentage
from utils.translations import action_label, tr

lang = prepare_page()
flash_messages(lang)
user = current_user()


# --------------------------------------------------------------------------- #
# Blocs
# --------------------------------------------------------------------------- #


def _shortcuts() -> None:
    section_heading(lang, tr("dash_shortcuts", lang))
    cols = st.columns(4)
    targets = [
        ("pages/1_Orientation.py", "dash_take_quiz", "🧭"),
        ("pages/2_Ecoles_Formations.py", "dash_browse_schools", "🎓"),
        ("pages/3_Preparation_Concours.py", "dash_prepare", "📚"),
        ("pages/5_Mon_Profil.py", "dash_edit_profile", "👤"),
    ]
    for col, (path, key, icon) in zip(cols, targets):
        with col:
            st.page_link(path, label=tr(key, lang), icon=icon, use_container_width=True)


def _profile_block(profile) -> None:
    section_heading(lang, tr("dash_profile", lang))
    if profile is None or not any(
        [
            profile.bac_series,
            profile.bac_year,
            profile.city,
            profile.average is not None,
            profile.favorite_subjects,
            profile.interests,
            profile.desired_fields,
        ]
    ):
        st.info(tr("dash_profile_empty", lang))
        return
    rows = [
        (tr("label_bac_series", lang), profile.bac_series),
        (tr("label_bac_year", lang), str(profile.bac_year) if profile.bac_year else None),
        (tr("label_city", lang), profile.city),
        (
            tr("label_average", lang),
            f"{profile.average:g}" if profile.average is not None else None,
        ),
        (
            tr("label_favorite_subjects", lang),
            " · ".join(_label(v) for v in profile.favorite_subjects) or None,
        ),
        (tr("label_interests", lang), " · ".join(_label(v) for v in profile.interests) or None),
        (
            tr("label_desired_fields", lang),
            " · ".join(_label(v) for v in profile.desired_fields) or None,
        ),
        (tr("label_geo_pref", lang), profile.geographic_preference),
        (tr("label_budget_pref", lang), profile.budget_preference),
    ]
    with st.container(border=True):
        for label, value in rows:
            if value:
                st.markdown(f"**{label}** : {value}")
            else:
                st.caption(f"{label} : {unknown(lang)}")


def _label(key: str) -> str:
    from utils.translations import T, tr as _tr

    return _tr(key, lang) if key in T else key


def _favorites_block(favorites: list) -> None:
    section_heading(lang, tr("dash_favorites", lang))
    schools = [f for f in favorites if f.target_type == "school"]
    programs = [f for f in favorites if f.target_type == "program"]
    if not schools and not programs:
        st.info(tr("fav_empty", lang))
        return
    cols = st.columns(2)
    with cols[0]:
        st.markdown(f"**{tr('fav_schools', lang)}** ({len(schools)})")
        for fav in schools[:5]:
            st.markdown(f"- {fav.school.name if fav.school else '—'}")
    with cols[1]:
        st.markdown(f"**{tr('fav_programs', lang)}** ({len(programs)})")
        for fav in programs[:5]:
            st.markdown(f"- {fav.program.name if fav.program else '—'}")


def _quiz_block(user_id: int) -> None:
    section_heading(lang, tr("dash_quiz_progress", lang))
    with db_session() as session:
        rows = quiz_service.progress(session, user_id)
        attempts = quiz_service.latest_attempts(session, user_id, limit=5)
    if not rows:
        st.info(tr("prep_no_history", lang))
        return
    cols = st.columns(min(3, len(rows)))
    for col, row in zip(cols, rows):
        with col, st.container(border=True):
            st.markdown(f"**{row['subject']}**")
            st.progress(min(1.0, row["best"] / 100.0))
            st.caption(f"{tr('prep_best', lang)} : {row['best']:g} % · {row['attempts']} {tr('prep_attempts_count', lang).lower()}")
    if attempts:
        with db_session() as session:
            st.caption(
                " · ".join(
                    f"{(repo.get_quiz(session, a.quiz_id).title if repo.get_quiz(session, a.quiz_id) else '?')}"
                    f" — {a.score}/{a.total} ({format_datetime(a.created_at, lang)})"
                    for a in attempts
                )
            )


def _orientation_block(user_id: int) -> None:
    section_heading(lang, tr("dash_orientation_results", lang))
    with db_session() as session:
        result = ori.last_result(session, user_id)
    if result is None:
        st.info(tr("dash_no_orientation", lang))
        st.page_link("pages/1_Orientation.py", label=tr("dash_take_quiz", lang), icon="🧭")
        return
    for rank, pathway in enumerate(result.result.get("pathways", []), start=1):
        pathway_card(lang, pathway, rank)
    matches = result.result.get("program_matches", [])
    if matches:
        st.caption(tr("ori_matches", lang))
        for match in matches[:3]:
            match_card(lang, match)


def _recommendations_block(user_id: int) -> None:
    section_heading(lang, tr("dash_recommendations", lang))
    with db_session() as session:
        result = ori.last_result(session, user_id)
        programs = repo.list_all_programs(session)
    if result is None:
        st.info(tr("dash_no_orientation", lang))
        return
    matches = result.result.get("program_matches", [])
    if not matches:
        st.info(tr("ori_match_no_rule", lang))
        return
    for match in matches[:4]:
        match_card(lang, match)


def _deadlines_block() -> None:
    section_heading(lang, tr("dash_deadlines", lang))
    with db_session() as session:
        confirmed = school_service.confirmed_deadlines(session)
    if not confirmed:
        st.info(tr("dl_none_confirmed", lang))
    for deadline in confirmed[:5]:
        context = deadline.school.name if deadline.school else (
            deadline.program.name if deadline.program else ""
        )
        deadline_card(lang, deadline, context_label=context)
    st.caption(tr("dl_reminder_note", lang))


def _activity_block(user_id: int) -> None:
    section_heading(lang, tr("dash_activity", lang))
    with db_session() as session:
        logs = repo.list_audit_logs(session, limit=8, actor_id=user_id)
    if not logs:
        st.info(tr("dash_no_activity", lang))
        return
    with st.container(border=True):
        for entry in logs:
            st.markdown(
                f"- {action_label(entry.action, lang)} — {format_datetime(entry.created_at, lang)}"
            )


def _guest_view() -> None:
    html_block(
        f'<div class="ns-hero"><div class="ns-flag">🎓 NextStep Maroc</div>'
        f'<h1>{h(tr("dash_guest_title", lang))}</h1>'
        f'<div class="ns-lead">{h(tr("dash_guest_text", lang))}</div></div>'
    )
    _shortcuts()
    notice("demo", tr("common_demo_notice", lang))
    _deadlines_block()


# --------------------------------------------------------------------------- #
# Page
# --------------------------------------------------------------------------- #

heading(lang, tr("dash_title", lang), kicker=tr("nav_dashboard", lang))

if user is None:
    _guest_view()
else:
    profile_name = None
    with db_session() as session:
        profile = repo.get_profile(session, user.id)
        favorites = school_service.list_favorites(session, user.id)
    profile_name = (profile.display_name if profile and profile.display_name else None) or user.email.split("@")[0]
    st.success(tr("dash_welcome", lang, name=profile_name))

    counts = {
        "schools": sum(1 for f in favorites if f.target_type == "school"),
        "programs": sum(1 for f in favorites if f.target_type == "program"),
    }
    cols = st.columns(4)
    with cols[0]:
        stat_tile(counts["schools"], tr("fav_schools", lang))
    with cols[1]:
        stat_tile(counts["programs"], tr("fav_programs", lang))
    with cols[2]:
        with db_session() as session:
            attempts_count = len(quiz_service.history(session, user.id))
        stat_tile(attempts_count, tr("prep_attempts_count", lang))
    with cols[3]:
        with db_session() as session:
            has_result = ori.last_result(session, user.id) is not None
        stat_tile(tr("common_yes", lang) if has_result else tr("common_no", lang), tr("dash_orientation_results", lang))

    _shortcuts()
    _profile_block(profile)
    _favorites_block(favorites)
    _quiz_block(user.id)
    _orientation_block(user.id)
    _recommendations_block(user.id)
    _deadlines_block()
    _activity_block(user.id)

footer(lang)
