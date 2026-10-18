"""Page — Administration et modération.

Destinée aux rôles ``moderateur`` et ``administrateur`` ; les opérations
sensibles (comptes, écoles, formations, critères, échéances, QCM, journal)
sont réservées à l'``administrateur``. Les services rejettent ces appels par
``PermissionDenied`` même si un bouton était affiché : le contrôle n'est pas
dépendant de l'interface.
"""

from __future__ import annotations

import datetime as dt
import json

import pandas as pd
import streamlit as st

from components.forms import show_service_error
from components.layout import badge, footer, h, heading, html_block, notice, section_heading
from components.navigation import (
    current_language,
    current_user,
    flash_messages,
    is_staff,
    prepare_page,
    set_flash,
)
from database import repositories as repo
from database.connection import db_session
from database.models import BAC_SERIES, CRITERION_TYPES, DEADLINE_TYPES, ROLES, VERIFICATION_STATUSES
from services import admin_service, resource_service, school_service
from utils.exceptions import NextStepError, PermissionDenied
from utils.helpers import format_date, format_datetime
from utils.translations import action_label, tr

lang = prepare_page()
flash_messages(lang)
user = current_user()

heading(lang, tr("adm_title", lang), kicker=tr("nav_admin", lang))

if not is_staff(user):
    st.error(tr("adm_access_denied", lang))
    footer(lang)
    st.stop()

can_admin = user.role == "administrateur"

STATUS_OPTIONS = list(VERIFICATION_STATUSES)
ROLE_KEYS = {"candidat": "role_candidat", "moderateur": "role_moderateur", "administrateur": "role_administrateur"}
LANGUAGES_LABELS = {"fr": "Français", "ar": "العربية", "en": "English"}


def _status_label(status: str) -> str:
    keys = {
        "official_verified": "status_official",
        "pending_verification": "status_pending",
        "unknown": "status_unknown",
        "community": "status_community",
        "demo": "status_demo",
    }
    return f"{tr(keys.get(status, 'status_unknown'), lang)} ({status})"


def _admin_only() -> bool:
    if not can_admin:
        st.info(tr("adm_only_admin", lang))
    return can_admin


# --------------------------------------------------------------------------- #
# Onglet : statistiques
# --------------------------------------------------------------------------- #


def _tab_stats() -> None:
    with db_session() as session:
        data = admin_service.staff_stats(session, user)
    pairs = [
        (data.get("schools", 0), "adm_schools"),
        (data.get("programs", 0), "adm_programs"),
        (data.get("quizzes", 0), "adm_quizzes"),
        (data.get("questions", 0), "adm_questions"),
        (data.get("users", 0), "adm_users"),
        (data.get("attempts", 0), "prep_attempts_count"),
        (data.get("favorites", 0), "nav_favorites"),
        (data.get("deadlines_confirmed", 0), "dl_confirmed"),
        (data.get("resources_pending", 0), "res_status_pending"),
        (data.get("reports_open", 0), "adm_reports"),
    ]
    for row_start in range(0, len(pairs), 5):
        cols = st.columns(5)
        for col, (value, key) in zip(cols, pairs[row_start : row_start + 5]):
            with col:
                st.metric(tr(key, lang), value)


# --------------------------------------------------------------------------- #
# Onglet : utilisateurs
# --------------------------------------------------------------------------- #


def _tab_users() -> None:
    if not _admin_only():
        return
    with db_session() as session:
        users = admin_service.users_list(session, user)

    rows = [
        {
            tr("adm_col_user", lang): u.email,
            tr("label_role", lang): tr(ROLE_KEYS.get(u.role, "role_candidat"), lang),
            tr("adm_col_state", lang): tr("adm_col_active" if u.is_active else "adm_col_inactive", lang),
            tr("adm_col_date", lang): format_date(u.created_at.date() if u.created_at else None, lang),
        }
        for u in users
    ]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    emails = [u.email for u in users]
    if not emails:
        return
    target_email = st.selectbox(tr("adm_col_user", lang), options=emails, key="adm_user_pick")
    target = next((u for u in users if u.email == target_email), None)
    if target is None:
        return

    c1, c2, c3 = st.columns(3)
    new_role = c1.selectbox(
        tr("label_role", lang),
        options=list(ROLES),
        index=list(ROLES).index(target.role),
        format_func=lambda role: tr(ROLE_KEYS.get(role, "role_candidat"), lang),
        key="adm_role_pick",
    )
    if c2.button(tr("btn_save", lang), key="adm_role_save", use_container_width=True):
        try:
            with db_session() as session:
                admin_service.set_user_role(session, user, target.id, new_role)
            set_flash("adm_user_role_updated")
            st.rerun()
        except NextStepError as exc:
            show_service_error(lang, exc)
    activate_label = tr("adm_deactivate", lang) if target.is_active else tr("adm_activate", lang)
    if c3.button(activate_label, key="adm_active_toggle", use_container_width=True):
        try:
            with db_session() as session:
                admin_service.set_user_active(session, user, target.id, not target.is_active)
            set_flash("adm_user_state_updated")
            st.rerun()
        except NextStepError as exc:
            show_service_error(lang, exc)


# --------------------------------------------------------------------------- #
# Onglet : écoles et formations
# --------------------------------------------------------------------------- #


def _tab_schools() -> None:
    if not _admin_only():
        return
    with db_session() as session:
        school_rows = _school_rows(session)
        programs = repo.list_all_programs(session)

    tab_a, tab_b, tab_c = st.tabs(
        [tr("adm_schools", lang), tr("adm_programs", lang), tr("adm_rules", lang)]
    )

    with tab_a:
        with st.form("adm_add_school"):
            st.markdown(f"**{tr('adm_form_school_name', lang)}**")
            name = st.text_input(tr("adm_form_school_name", lang), key="as_name")
            c1, c2, c3 = st.columns(3)
            city = c1.text_input(tr("sch_filter_city", lang), key="as_city")
            domain = c2.text_input(tr("sch_filter_domain", lang), key="as_domain")
            school_type = c3.text_input(tr("sch_filter_type", lang), key="as_type")
            url = st.text_input(tr("common_official_url", lang), key="as_url")
            description = st.text_area(tr("res_label_description", lang), key="as_desc")
            status = st.selectbox(
                tr("adm_form_verification", lang),
                options=STATUS_OPTIONS,
                format_func=_status_label,
                key="as_status",
            )
            if st.form_submit_button(tr("btn_save", lang), use_container_width=True):
                try:
                    with db_session() as session:
                        admin_service.create_school(
                            session,
                            user,
                            {
                                "name": name,
                                "city": city,
                                "domain": domain,
                                "school_type": school_type,
                                "official_url": url or None,
                                "description": description,
                                "verification_status": status,
                            },
                        )
                    set_flash("adm_created")
                    st.rerun()
                except NextStepError as exc:
                    show_service_error(lang, exc)

        section_heading(lang, tr("adm_schools", lang))
        st.dataframe(pd.DataFrame(school_rows), use_container_width=True, hide_index=True)
        ids = [row["id"] for row in school_rows]
        if ids:
            pick = st.selectbox(
                tr("adm_form_school_name", lang),
                options=ids,
                format_func=lambda i: next((r["name"] for r in school_rows if r["id"] == i), str(i)),
                key="adm_school_pick",
            )
            if st.button(tr("adm_deactivate", lang), key="adm_school_toggle"):
                current_active = next((r["active"] for r in school_rows if r["id"] == pick), True)
                try:
                    with db_session() as session:
                        admin_service.set_school_active(session, user, pick, not current_active)
                    set_flash("adm_deactivated" if not current_active else "adm_updated")
                    st.rerun()
                except NextStepError as exc:
                    show_service_error(lang, exc)

    with tab_b:
        with st.form("adm_add_program"):
            school_ids = [r["id"] for r in school_rows if r["active"]]
            if not school_ids:
                st.info(tr("sch_no_result", lang))
            else:
                school_id = st.selectbox(
                    tr("adm_form_program_school", lang),
                    options=school_ids,
                    format_func=lambda i: next((r["name"] for r in school_rows if r["id"] == i), str(i)),
                    key="ap_school",
                )
                pname = st.text_input(tr("adm_form_program_name", lang), key="ap_name")
                c1, c2 = st.columns(2)
                degree = c1.text_input(tr("sch_filter_degree", lang), key="ap_degree")
                domain = c2.text_input(tr("sch_filter_domain", lang), key="ap_domain")
                c3, c4 = st.columns(2)
                duration = c3.number_input(
                    tr("sch_program_duration", lang), min_value=0.0, max_value=12.0, value=0.0, step=0.5, key="ap_duration"
                )
                fees = c4.number_input(
                    tr("sch_program_fees", lang) + " (MAD)", min_value=0.0, value=0.0, step=500.0, key="ap_fees"
                )
                status = st.selectbox(
                    tr("adm_form_verification", lang),
                    options=STATUS_OPTIONS,
                    format_func=_status_label,
                    key="ap_status",
                )
                if st.form_submit_button(tr("btn_save", lang), use_container_width=True):
                    try:
                        with db_session() as session:
                            admin_service.create_program(
                                session,
                                user,
                                {
                                    "school_id": school_id,
                                    "name": pname,
                                    "degree_level": degree or None,
                                    "domain": domain or None,
                                    "duration_years": duration or None,
                                    "tuition_fees_mad": fees or None,
                                    "verification_status": status,
                                },
                            )
                        set_flash("adm_created")
                        st.rerun()
                    except NextStepError as exc:
                        show_service_error(lang, exc)

        if programs:
            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "id": p.id,
                            tr("adm_form_program_name", lang): p.name,
                            tr("adm_form_program_school", lang): p.school.name if p.school else "",
                            tr("common_status", lang): p.verification_status,
                            tr("sch_program_fees", lang): p.tuition_fees_mad or "—",
                        }
                        for p in programs
                    ]
                ),
                use_container_width=True,
                hide_index=True,
            )

    with tab_c:
        if not programs:
            st.info(tr("sch_no_result", lang))
            return
        with st.form("adm_add_rule"):
            program_ids = [p.id for p in programs]
            program_id = st.selectbox(
                tr("adm_form_rule_program", lang),
                options=program_ids,
                format_func=lambda i: next((p.name for p in programs if p.id == i), str(i)),
                key="ar_program",
            )
            label = st.text_input(tr("adm_rules", lang), key="ar_label")
            source = st.text_input(tr("common_source", lang), key="ar_source")
            status = st.selectbox(
                tr("adm_form_verification", lang),
                options=STATUS_OPTIONS,
                format_func=_status_label,
                key="ar_status",
            )
            ctype = st.selectbox(
                tr("adm_rules", lang) + " — type",
                options=list(CRITERION_TYPES),
                key="ar_type",
                format_func=lambda t: {
                    "bac_series": tr("sch_criteria_series", lang),
                    "min_average": tr("sch_criteria_average", lang),
                    "exam_type": tr("sch_criteria_exam", lang),
                    "other": tr("sch_criteria_other", lang),
                }[t],
            )
            required = st.checkbox(tr("sch_criteria_required", lang), value=True, key="ar_required")
            if ctype == "bac_series":
                raw = st.multiselect(
                    tr("sch_series_list", lang),
                    options=list(BAC_SERIES),
                    key="ar_series",
                )
                value = raw
            elif ctype == "min_average":
                value = st.number_input(
                    tr("sch_criteria_average", lang) + " (/20)",
                    min_value=0.0,
                    max_value=20.0,
                    value=12.0,
                    step=0.25,
                    key="ar_avg",
                )
            else:
                value = st.text_input(tr("sch_criteria_other", lang), key="ar_text")
            description = st.text_input(tr("res_label_description", lang), key="ar_desc")
            if st.form_submit_button(tr("btn_save", lang), use_container_width=True):
                try:
                    with db_session() as session:
                        admin_service.add_admission_rule(
                            session,
                            user,
                            {
                                "program_id": program_id,
                                "label": label or None,
                                "source_name": source or None,
                                "verification_status": status,
                                "criteria": [
                                    {
                                        "criterion_type": ctype,
                                        "value": value,
                                        "operator": "in" if ctype == "bac_series" else ("gte" if ctype == "min_average" else "text"),
                                        "is_required": required,
                                        "description": description or None,
                                        "verification_status": status,
                                    }
                                ],
                            },
                        )
                    set_flash("adm_created")
                    st.rerun()
                except NextStepError as exc:
                    show_service_error(lang, exc)


def _school_rows(session) -> list[dict]:
    from database.models import School
    from sqlalchemy import select

    rows = []
    for school in session.scalars(select(School).order_by(School.name)).all():
        rows.append(
            {
                "id": school.id,
                "name": school.name,
                tr("sch_filter_city", lang): school.city or "—",
                tr("common_status", lang): school.verification_status,
                "active": school.is_active,
            }
        )
    return rows


# --------------------------------------------------------------------------- #
# Onglet : échéances
# --------------------------------------------------------------------------- #


def _tab_deadlines() -> None:
    if not _admin_only():
        return
    with db_session() as session:
        schools = _school_rows(session)
        programs = repo.list_all_programs(session)
        deadlines = school_service.all_deadlines(session)

    with st.form("adm_add_deadline"):
        title = st.text_input(tr("adm_form_deadline_title", lang), key="dl_title")
        c1, c2 = st.columns(2)
        dtype = c1.selectbox(
            tr("dl_title", lang) + " — type",
            options=list(DEADLINE_TYPES),
            key="dl_type",
            format_func=lambda t: {
                "candidature": tr("dl_type_candidature", lang),
                "concours": tr("dl_type_concours", lang),
                "resultat": tr("dl_type_resultat", lang),
                "autre": tr("dl_type_autre", lang),
            }[t],
        )
        has_date = c2.checkbox(tr("common_yes", lang), value=True, key="dl_has_date")
        event_date = st.date_input(
            tr("adm_form_deadline_date", lang),
            value=dt.date.today() + dt.timedelta(days=30),
            key="dl_date",
        ) if has_date else None
        c3, c4 = st.columns(2)
        school_ids = [r["id"] for r in schools]
        school_id = c3.selectbox(
            tr("adm_form_program_school", lang),
            options=[""] + school_ids,
            format_func=lambda i: next((r["name"] for r in schools if r["id"] == i), "") if i else tr("common_none", lang),
            key="dl_school",
        )
        program_ids = [p.id for p in programs]
        program_id = c4.selectbox(
            tr("adm_form_rule_program", lang),
            options=[""] + program_ids,
            format_func=lambda i: next((p.name for p in programs if p.id == i), "") if i else tr("common_none", lang),
            key="dl_program",
        )
        source = st.text_input(tr("common_source", lang), key="dl_source")
        status = st.selectbox(
            tr("adm_form_verification", lang),
            options=STATUS_OPTIONS,
            format_func=_status_label,
            key="dl_status",
        )
        if st.form_submit_button(tr("btn_save", lang), use_container_width=True):
            try:
                with db_session() as session:
                    admin_service.add_deadline(
                        session,
                        user,
                        {
                            "title": title,
                            "deadline_type": dtype,
                            "event_date": event_date.isoformat() if event_date else None,
                            "school_id": int(school_id) if school_id else None,
                            "program_id": int(program_id) if program_id else None,
                            "source_name": source or None,
                            "verification_status": status,
                        },
                    )
                set_flash("adm_created")
                st.rerun()
            except NextStepError as exc:
                show_service_error(lang, exc)

    section_heading(lang, tr("adm_deadlines", lang))
    if deadlines:
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "id": d.id,
                        tr("adm_form_deadline_title", lang): d.title,
                        tr("adm_col_date", lang): d.event_date.isoformat() if d.event_date else tr("dl_date_unknown", lang),
                        tr("common_status", lang): d.verification_status,
                        tr("common_source", lang): d.source_name or "—",
                    }
                    for d in deadlines
                ]
            ),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info(tr("sch_no_deadline", lang))


# --------------------------------------------------------------------------- #
# Onglet : QCM
# --------------------------------------------------------------------------- #


def _tab_quizzes() -> None:
    if not _admin_only():
        return
    with db_session() as session:
        quizzes = repo.list_quizzes(session)

    with st.form("adm_add_quiz"):
        st.markdown(f"**{tr('adm_quizzes', lang)}**")
        title = st.text_input(tr("adm_form_quiz_title", lang), key="qz_title")
        c1, c2, c3 = st.columns(3)
        subject = c1.text_input(tr("adm_form_quiz_subject", lang), key="qz_subject")
        qlang = c2.selectbox(
            tr("common_language", lang),
            options=["fr", "ar", "en"],
            format_func=lambda code: LANGUAGES_LABELS.get(code, code),
            key="qz_lang",
        )
        difficulty = c3.selectbox(
            tr("prep_difficulty", lang),
            options=["", "facile", "moyen", "difficile"],
            format_func=lambda v: v if v else tr("common_none", lang),
            key="qz_diff",
        )
        description = st.text_area(tr("res_label_description", lang), key="qz_desc")
        if st.form_submit_button(tr("btn_save", lang), use_container_width=True):
            try:
                with db_session() as session:
                    admin_service.create_quiz(
                        session,
                        user,
                        title,
                        subject,
                        language=qlang,
                        difficulty=difficulty or None,
                        description=description,
                    )
                set_flash("adm_created")
                st.rerun()
            except NextStepError as exc:
                show_service_error(lang, exc)

    if quizzes:
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "id": q.id,
                        tr("adm_form_quiz_title", lang): q.title,
                        tr("adm_form_quiz_subject", lang): q.subject,
                        tr("adm_questions", lang): len(q.questions),
                        tr("common_language", lang): q.language,
                    }
                    for q in quizzes
                ]
            ),
            use_container_width=True,
            hide_index=True,
        )

    quiz_ids = [q.id for q in quizzes]
    if not quiz_ids:
        return
    selected = st.selectbox(
        tr("adm_form_quiz_title", lang),
        options=quiz_ids,
        format_func=lambda i: next((q.title for q in quizzes if q.id == i), str(i)),
        key="adm_quiz_pick",
    )
    with st.form("adm_add_question"):
        st.markdown(f"**{tr('adm_questions', lang)}**")
        statement = st.text_area(tr("adm_form_question", lang), key="aq_statement")
        options_text = st.text_area(tr("adm_form_options", lang), key="aq_options", height=140)
        c1, c2 = st.columns(2)
        correct_index = c1.number_input(
            tr("adm_form_correct", lang), min_value=1, max_value=6, value=1, step=1, key="aq_correct"
        )
        qlang = c2.selectbox(
            tr("common_language", lang),
            options=["fr", "ar", "en"],
            format_func=lambda code: LANGUAGES_LABELS.get(code, code),
            key="aq_lang",
        )
        explanation = st.text_area(tr("adm_form_explanation", lang), key="aq_explanation")
        difficulty = st.selectbox(
            tr("prep_difficulty", lang),
            options=["", "facile", "moyen", "difficile"],
            format_func=lambda v: v if v else tr("common_none", lang),
            key="aq_diff",
        )
        if st.form_submit_button(tr("btn_save", lang), use_container_width=True):
            options = [line.strip() for line in (options_text or "").splitlines() if line.strip()]
            try:
                with db_session() as session:
                    admin_service.add_question(
                        session,
                        user,
                        selected,
                        {
                            "statement": statement,
                            "options": options,
                            "correct_index": int(correct_index) - 1,
                            "explanation": explanation or None,
                            "language": qlang,
                            "difficulty": difficulty or None,
                        },
                    )
                set_flash("adm_created")
                st.rerun()
            except NextStepError as exc:
                show_service_error(lang, exc)


# --------------------------------------------------------------------------- #
# Onglet : ressources et signalements
# --------------------------------------------------------------------------- #


def _tab_moderation() -> None:
    section_heading(lang, tr("adm_resources", lang))
    with db_session() as session:
        pending = resource_service.pending_resources(session, user)
        reports = resource_service.list_reports(session, user, status="open")

    if not pending:
        st.info(tr("res_empty", lang))
    for resource in pending:
        with st.container(border=True):
            html_block(f"<div style='font-weight:700'>{h(resource.title)}</div>")
            st.caption(
                f"{resource.category or '—'} · {tr('res_label_author', lang)}: "
                f"{resource.author_name or resource.submitter.email if resource.submitter else '—'}"
            )
            st.write(resource.description or "")
            if resource.content:
                with st.expander(tr("btn_details", lang)):
                    st.write(resource.content)
            c1, c2 = st.columns([2, 1])
            new_status = c1.selectbox(
                tr("common_status", lang),
                options=list(resource_service.RESOURCE_STATUS_VALUES),
                format_func=lambda s: tr(f"res_status_{s}", lang),
                key=f"mod_status_{resource.id}",
                label_visibility="collapsed",
            )
            note = c2.text_input(
                tr("adm_report_reason", lang),
                key=f"mod_note_{resource.id}",
                label_visibility="collapsed",
                placeholder=tr("adm_form_explanation", lang),
            )
            if st.button(tr("btn_save", lang), key=f"mod_save_{resource.id}"):
                try:
                    with db_session() as session:
                        resource_service.moderate_resource(session, user, resource.id, new_status, note)
                    set_flash("adm_status_updated")
                    st.rerun()
                except NextStepError as exc:
                    show_service_error(lang, exc)

    section_heading(lang, tr("adm_reports", lang))
    if not reports:
        st.info(tr("adm_audit_empty", lang))
    for report in reports:
        with st.container(border=True):
            html_block(
                f"<div style='font-weight:700'>{h(report.resource.title if report.resource else '?')}</div>"
            )
            st.caption(f"{tr('adm_report_reason', lang)} : {report.reason}")
            c1, c2, _ = st.columns([1, 1, 2])
            if c1.button(tr("adm_resolve", lang), key=f"rep_res_{report.id}"):
                _resolve(report.id, "resolved")
            if c2.button(tr("adm_dismiss", lang), key=f"rep_dis_{report.id}"):
                _resolve(report.id, "dismissed")


def _resolve(report_id: int, status: str) -> None:
    try:
        with db_session() as session:
            resource_service.resolve_report(session, user, report_id, status)
        set_flash("adm_report_updated")
        st.rerun()
    except NextStepError as exc:
        show_service_error(lang, exc)


# --------------------------------------------------------------------------- #
# Onglet : journal d'audit
# --------------------------------------------------------------------------- #


def _tab_audit() -> None:
    if not _admin_only():
        return
    with db_session() as session:
        logs = admin_service.audit_logs(session, user, limit=200)
    if not logs:
        st.info(tr("adm_audit_empty", lang))
        return
    rows = []
    for entry in logs:
        actor = entry.actor.email if entry.actor else "—"
        detail = json.dumps(entry.detail, ensure_ascii=False) if entry.detail else ""
        rows.append(
            {
                tr("adm_col_date", lang): format_datetime(entry.created_at, lang),
                tr("adm_col_actor", lang): actor,
                tr("adm_col_action", lang): action_label(entry.action, lang),
                "entity": f"{entry.entity_type or ''}#{entry.entity_id or ''}",
                tr("adm_col_detail", lang): detail[:80],
            }
        )
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


# --------------------------------------------------------------------------- #
# Page
# --------------------------------------------------------------------------- #

tabs = st.tabs(
    [
        tr("adm_stats", lang),
        tr("adm_users", lang),
        tr("adm_schools", lang),
        tr("adm_deadlines", lang),
        tr("adm_quizzes", lang),
        tr("adm_resources", lang),
        tr("adm_audit", lang),
    ]
)
with tabs[0]:
    _tab_stats()
with tabs[1]:
    _tab_users()
with tabs[2]:
    _tab_schools()
with tabs[3]:
    _tab_deadlines()
with tabs[4]:
    _tab_quizzes()
with tabs[5]:
    _tab_moderation()
with tabs[6]:
    _tab_audit()

footer(lang)
