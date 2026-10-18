"""Page — Préparation aux concours : fiches de révision et QCM interactifs.

Parcours QCM : énoncé → choix d'une réponse → validation → correction
expliquée → question suivante → score enregistré (si connecté) + historique.
La correction est calculée côté serveur (``services.quiz_service``).
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from components.cards import quiz_card, resource_card
from components.forms import show_service_error
from components.layout import badge, footer, h, heading, html_block, notice, section_heading, unknown
from components.navigation import (
    current_language,
    current_user,
    flash_messages,
    prepare_page,
    set_flash,
)
from database import repositories as repo
from database.connection import db_session
from services import quiz_service, resource_service
from utils.exceptions import NextStepError
from utils.helpers import format_datetime, percentage
from utils.translations import tr

lang = prepare_page()
flash_messages(lang)
user = current_user()


# --------------------------------------------------------------------------- #
# Données
# --------------------------------------------------------------------------- #


def _quizzes():
    with db_session() as session:
        return quiz_service.available_quizzes(session)


def _attempts_stats():
    if user is None:
        return {}, {}
    with db_session() as session:
        attempts = quiz_service.history(session, user.id)
    best: dict[int, float] = {}
    count: dict[int, int] = {}
    for attempt in attempts:
        count[attempt.quiz_id] = count.get(attempt.quiz_id, 0) + 1
        pct = percentage(attempt.score, attempt.total)
        best[attempt.quiz_id] = max(best.get(attempt.quiz_id, 0.0), pct)
    return count, best


# --------------------------------------------------------------------------- #
# Fiches de révision
# --------------------------------------------------------------------------- #


def _sheets() -> None:
    with db_session() as session:
        resources = resource_service.published_resources(session, category="fiche_de_revision")
        if not resources:
            resources = resource_service.published_resources(session)
    if not resources:
        st.info(tr("res_empty", lang))
        return
    notice("demo", tr("prep_demo_notice", lang))
    for resource in resources:
        reported = resource_card(
            lang,
            resource,
            report_key=f"report_sheet_{resource.id}" if user else None,
        )
        if reported and user is not None:
            st.session_state["reporting_resource_id"] = resource.id
            st.rerun()

    reporting_id = st.session_state.get("reporting_resource_id")
    if reporting_id:
        _report(int(reporting_id))


def _report(resource_id: int) -> None:
    st.markdown(f"**{tr('res_report_title', lang)}**")
    reason = st.text_area(
        tr("res_report_title", lang),
        key=f"report_reason_{resource_id}",
        label_visibility="collapsed",
    )
    c1, c2 = st.columns(2)
    if c1.button(tr("btn_submit", lang), key=f"send_report_{resource_id}"):
        if not reason or len(reason.strip()) < 5:
            st.error(tr("error_required", lang))
            return
        try:
            with db_session() as session:
                resource_service.report_resource(session, user.id, resource_id, reason.strip())
            st.session_state.pop("reporting_resource_id", None)
            set_flash("res_report_notice")
            st.rerun()
        except NextStepError as exc:
            show_service_error(lang, exc)
    if c2.button(tr("btn_cancel", lang), key=f"cancel_report_{resource_id}"):
        st.session_state.pop("reporting_resource_id", None)
        st.rerun()


# --------------------------------------------------------------------------- #
# QCM
# --------------------------------------------------------------------------- #


def _start_quiz(quiz_id: int) -> None:
    st.session_state["active_quiz_id"] = quiz_id
    st.session_state["quiz_index"] = 0
    st.session_state["quiz_answers"] = {}
    st.session_state["quiz_corrections"] = {}
    st.session_state["quiz_result"] = None
    st.rerun()


def _leave_quiz() -> None:
    for key in ("active_quiz_id", "quiz_index", "quiz_answers", "quiz_corrections", "quiz_result"):
        st.session_state.pop(key, None)
    st.rerun()


def _quiz_list() -> None:
    quizzes = _quizzes()
    if not quizzes:
        st.info(tr("prep_no_quiz", lang))
        return
    count, best = _attempts_stats()
    for quiz in quizzes:
        started = quiz_card(
            lang,
            quiz,
            attempts_for_quiz=count.get(quiz.id, 0),
            best=best.get(quiz.id),
        )
        if started:
            _start_quiz(quiz.id)


def _summary(quiz, result: dict) -> None:
    st.success(tr("prep_score", lang, score=result["score"], total=result["total"], pct=result["pct"]))
    if not result.get("saved"):
        st.info(tr("prep_login_required", lang))
    section_heading(lang, tr("prep_explanation", lang))
    for correction in result.get("corrections", []):
        icon = "✅" if correction["is_correct"] else "❌"
        html_block(
            f"<div class='ns-option'><b>{icon}</b> {h(correction['statement'])}<br>"
            f"<span class='ns-small'><b>{h(tr('prep_correct', lang))} :</b> {h(correction['correct_text'])}</span>"
            + (
                f"<br><span class='ns-muted ns-small'>{h(correction['explanation'])}</span>"
                if correction["explanation"]
                else ""
            )
            + "</div>"
        )
    if st.button(tr("btn_back", lang), key="leave_quiz_result"):
        _leave_quiz()


def _run_quiz(quiz) -> None:
    answers: dict = st.session_state.setdefault("quiz_answers", {})
    corrections: dict = st.session_state.setdefault("quiz_corrections", {})
    result = st.session_state.get("quiz_result")
    index = int(st.session_state.get("quiz_index", 0))

    html_block(f"<div class='ns-title-sm'>{h(quiz.subject)} — {h(quiz.title)}</div>")
    html_block(badge(lang, quiz.validation_status))
    st.caption(tr("prep_demo_notice", lang))

    if result is not None:
        _summary(quiz, result)
        return

    payload = quiz_service.question_payload(quiz, index)
    st.progress((index + 1) / max(1, payload["total"]))
    st.caption(
        tr("prep_question_of", lang, current=index + 1, total=payload["total"])
    )

    question_id = payload["id"]
    validated = corrections.get(str(question_id))

    if validated:
        if validated["is_correct"]:
            st.success(f"**{tr('prep_correct', lang)}**")
        else:
            st.error(f"**{tr('prep_incorrect', lang)}**")
        st.markdown(f"**{tr('prep_explanation', lang)}**")
        st.write(validated["explanation"] or unknown(lang))
        st.caption(
            f"{tr('prep_correct', lang)} : {validated['correct_text']}"
            + (f" — {tr('prep_incorrect', lang)} : {validated['chosen_text']}" if validated["chosen_text"] and not validated["is_correct"] else "")
        )
        is_last = index + 1 >= payload["total"]
        label = tr("prep_finish", lang) if is_last else tr("prep_next", lang)
        if st.button(label, key="quiz_next", use_container_width=True):
            if is_last:
                _submit(quiz, answers)
            else:
                st.session_state["quiz_index"] = index + 1
                st.rerun()
        if st.button(tr("btn_back", lang), key="quiz_abort", use_container_width=True):
            st.info(tr("prep_leave_warning", lang))
            _leave_quiz()
        return

    with st.form(f"quiz_form_{question_id}"):
        st.markdown(f"### {payload['statement']}")
        st.radio(
            tr("ori_select_one", lang),
            options=[option["id"] for option in payload["options"]],
            format_func=lambda option_id: next(
                (o["text"] for o in payload["options"] if o["id"] == option_id), ""
            ),
            key=f"q_{quiz.id}_{question_id}",
            label_visibility="collapsed",
        )
        submitted = st.form_submit_button(tr("prep_validate", lang), use_container_width=True)
    if payload["provenance"]:
        st.caption(f"{tr('prep_provenance', lang)} : {payload['provenance']}")

    if submitted:
        option_id = st.session_state.get(f"q_{quiz.id}_{question_id}")
        if option_id is None:
            st.error(tr("error_required", lang))
            return
        try:
            with db_session() as session:
                correction = quiz_service.validate_answer(session, question_id, option_id)
            corrections[str(question_id)] = correction
            answers[str(question_id)] = option_id
            st.rerun()
        except NextStepError as exc:
            show_service_error(lang, exc)


def _submit(quiz, answers: dict) -> None:
    payload_answers = [
        {"question_id": int(qid), "option_id": int(option_id)}
        for qid, option_id in answers.items()
    ]
    try:
        with db_session() as session:
            result = quiz_service.submit_attempt(
                session, user.id if user else None, quiz.id, payload_answers
            )
        st.session_state["quiz_result"] = result
        if result.get("saved"):
            set_flash("msg_saved")
        st.rerun()
    except NextStepError as exc:
        show_service_error(lang, exc)


# --------------------------------------------------------------------------- #
# Progression et historique
# --------------------------------------------------------------------------- #


def _progress_section() -> None:
    if user is None:
        st.info(tr("prep_login_required", lang))
        return
    with db_session() as session:
        rows = quiz_service.progress(session, user.id)
        attempts = quiz_service.history(session, user.id, limit=20)

    section_heading(lang, tr("prep_progress", lang))
    if not rows:
        st.info(tr("prep_no_history", lang))
    for row in rows:
        st.markdown(f"**{row['subject']}** — {tr('prep_best', lang)} {row['best']:g} %")
        st.progress(min(1.0, row["best"] / 100.0))

    if attempts:
        with db_session() as session:
            data = []
            for attempt in attempts:
                quiz = repo.get_quiz(session, attempt.quiz_id)
                data.append(
                    {
                        tr("adm_form_quiz_title", lang): quiz.title if quiz else str(attempt.quiz_id),
                        tr("prep_col_score", lang): (
                            f"{attempt.score}/{attempt.total} ({percentage(attempt.score, attempt.total):g} %)"
                        ),
                        tr("adm_col_date", lang): format_datetime(attempt.created_at, lang),
                    }
                )
        st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)
    else:
        st.caption(tr("prep_no_history", lang))


# --------------------------------------------------------------------------- #
# Page
# --------------------------------------------------------------------------- #

heading(
    lang,
    tr("prep_title", lang),
    subtitle=tr("prep_intro", lang),
    kicker=tr("nav_prep", lang),
)

tab_sheets, tab_quiz, tab_progress = st.tabs(
    [
        tr("prep_sheets", lang),
        tr("prep_quizzes", lang),
        tr("prep_progress", lang),
    ]
)
with tab_sheets:
    _sheets()
with tab_quiz:
    active_id = st.session_state.get("active_quiz_id")
    if active_id:
        with db_session() as session:
            try:
                quiz = quiz_service.get_quiz(session, int(active_id))
            except NextStepError:
                quiz = None
        if quiz is None:
            _leave_quiz()
        else:
            _run_quiz(quiz)
    else:
        _quiz_list()
with tab_progress:
    _progress_section()

footer(lang)
