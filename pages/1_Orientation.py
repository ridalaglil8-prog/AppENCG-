"""Page — Test d'orientation (assistant pas à pas, puis résultats).

Le calcul est délégué à ``services.orientation_service`` : déterministe,
explicable et testé unitairement. Cette page ne fait qu'afficher.
"""

from __future__ import annotations

import streamlit as st

from components.cards import match_card, pathway_card
from components.forms import show_service_error
from components.layout import (
    badge,
    footer,
    h,
    heading,
    html_block,
    notice,
    section_heading,
    unknown,
)
from components.navigation import (
    current_language,
    current_user,
    flash_messages,
    prepare_page,
    set_flash,
)
from database import repositories as repo
from database.connection import db_session
from services import orientation_service as ori
from utils.exceptions import NextStepError
from utils.translations import tr

lang = prepare_page()
flash_messages(lang)
user = current_user()


# --------------------------------------------------------------------------- #
# État de la session
# --------------------------------------------------------------------------- #


def _answers() -> dict:
    return st.session_state.setdefault("orientation_answers", {})


def _step() -> int:
    step = int(st.session_state.get("orientation_step", 0))
    return max(0, min(step, len(ori.STEPS) - 1))


def _clear_widget_state() -> None:
    """Vide les widgets du questionnaire (rétro-compatibilité d'une nouvelle passe)."""
    for key in [k for k in list(st.session_state) if k.startswith("ori_") and not k.startswith("orientation_")]:
        st.session_state.pop(key, None)


def _prefill_from_profile() -> None:
    if st.session_state.get("orientation_prefilled") or user is None:
        return
    with db_session() as session:
        profile = repo.get_profile(session, user.id)
    if profile is None:
        st.session_state["orientation_prefilled"] = True
        return
    answers = _answers()
    for key, value in ori.answers_from_profile(profile).items():
        answers.setdefault(key, value)
    st.session_state["orientation_prefilled"] = True


def _render_question(question: dict) -> None:
    answers = _answers()
    qid = question["id"]
    label = tr(question["label_key"], lang)
    help_text = tr(question.get("help_key", ""), lang) if question.get("help_key") else None
    options = question.get("options")

    if question["type"] == "multiselect":
        default = [v for v in answers.get(qid, []) if v in (options or [])]
        st.multiselect(
            label,
            options=options or [],
            default=default,
            format_func=lambda key: tr(key, lang),
            key=f"ori_{qid}",
            help=help_text,
        )
    elif question["type"] == "radio":
        current = answers.get(qid)
        index = (options or []).index(current) if current in (options or []) else None
        st.radio(
            label,
            options=options or [],
            index=index,
            format_func=lambda key: tr(key, lang),
            key=f"ori_{qid}",
            help=help_text,
        )
    elif question["type"] == "select":
        current = answers.get(qid)
        if current and options and current not in options:
            options = list(options) + [current]
        st.selectbox(
            label,
            options=[""] + list(options or []),
            index=([""] + list(options or [])).index(current) if current else 0,
            format_func=lambda value: value if value else tr("common_optional", lang),
            key=f"ori_{qid}",
            help=help_text,
        )
    elif question["type"] == "number":
        st.number_input(
            label,
            min_value=question.get("min", 0.0),
            max_value=question.get("max", 20.0),
            value=answers.get(qid),
            step=question.get("step", 0.25),
            key=f"ori_{qid}",
            help=help_text,
            format="%.2f",
        )


def _collect_step(step_index: int) -> dict:
    values: dict = {}
    for question in ori.questions_for_step(step_index):
        widget_key = f"ori_{question['id']}"
        values[question["id"]] = st.session_state.get(widget_key)
    return values


def _clean_values(step_index: int, values: dict) -> dict:
    """Normalise les valeurs d'étape (None/vide retirés)."""
    cleaned = {}
    for question in ori.questions_for_step(step_index):
        value = values.get(question["id"])
        if question["type"] == "number":
            if value is not None:
                cleaned[question["id"]] = float(value)
        elif value in (None, "", []):
            continue
        else:
            cleaned[question["id"]] = value
    return cleaned


def _show_results(computed: dict, saved: bool) -> None:
    section_heading(lang, tr("ori_results_title", lang), tr("ori_score_disclaimer", lang))
    notice("info", tr("ori_not_probability", lang))

    pathways = computed.get("pathways", [])
    if pathways:
        for rank, pathway in enumerate(pathways, start=1):
            pathway_card(lang, pathway, rank)
    else:
        st.info(tr("ori_note_no_pathway", lang))

    for note in computed.get("notes", []):
        params = {
            key: tr(value, lang) if key in ("preference",) else value
            for key, value in note.get("params", {}).items()
        }
        st.caption(tr(note["key"], lang, **params))

    section_heading(lang, tr("ori_matches", lang))
    html_block(badge(lang, "unknown"))
    st.caption(tr("ori_not_probability", lang))
    matches = computed.get("program_matches", [])
    if not matches:
        st.info(tr("ori_match_no_rule", lang))
    for match in matches:
        match_card(lang, match)

    if saved:
        st.success(tr("ori_save_ok", lang))
    elif user is None:
        st.info(tr("ori_login_required", lang))

    html_block(
        '<div class="ns-notice ns-notice-demo">'
        f'<b>{h(tr("ori_method_title", lang))}</b> — {h(tr("ori_method_text", lang))}</div>'
    )

    c1, c2, _ = st.columns([1, 1, 2])
    if c1.button(tr("ori_retake", lang), key="ori_retake", use_container_width=True):
        _clear_widget_state()
        st.session_state["orientation_step"] = 0
        st.session_state["orientation_answers"] = {}
        st.session_state["orientation_done"] = False
        st.session_state["orientation_prefilled"] = False
        st.session_state.pop("orientation_result", None)
        st.rerun()
    if c2.button(tr("btn_catalog", lang), key="ori_to_catalog", use_container_width=True):
        st.switch_page("pages/2_Ecoles_Formations.py")


# --------------------------------------------------------------------------- #
# Rendu
# --------------------------------------------------------------------------- #


def _run_questionnaire() -> None:
    total_steps = len(ori.STEPS)
    step = _step()

    if st.session_state.get("orientation_done"):
        _show_results(
            st.session_state.get("orientation_result", {}),
            saved=bool(st.session_state.get("orientation_saved")),
        )
        return

    _prefill_from_profile()
    progress_pct = step / total_steps
    st.progress(min(1.0, max(0.0, progress_pct)))
    st.caption(
        tr(
            "ori_progress",
            lang,
            current=min(step + 1, total_steps),
            total=total_steps,
        )
    )

    questions = ori.questions_for_step(step)
    html_block(f'<div class="ns-title-sm">{h(tr(questions[0]["label_key"], lang))}</div>')

    with st.form(f"orientation_step_{step}"):
        for question in questions:
            _render_question(question)
            help_text = tr(question.get("help_key", ""), lang) if question.get("help_key") else ""
            if help_text:
                st.caption(help_text)
        back_col, next_col = st.columns(2)
        can_back = step > 0
        back_clicked = back_col.form_submit_button(
            tr("btn_back", lang), disabled=not can_back, use_container_width=True
        )
        is_last = step == total_steps - 1
        next_label = tr("btn_view_results", lang) if is_last else tr("btn_next", lang)
        next_clicked = next_col.form_submit_button(next_label, use_container_width=True)

    if back_clicked and can_back:
        st.session_state["orientation_step"] = step - 1
        st.rerun()

    if next_clicked:
        values = _clean_values(step, _collect_step(step))
        errors = ori.validate_step_answers(step, values)
        if errors:
            st.error(
                tr("error_required", lang)
                + " "
                + ", ".join(tr(key, lang) for key in errors)
            )
            return
        _answers().update(values)
        if is_last:
            _compute_and_save()
        else:
            st.session_state["orientation_step"] = step + 1
            st.rerun()


def _compute_and_save() -> None:
    answers = _answers()
    with db_session() as session:
        profile = repo.get_profile(session, user.id) if user else None
        programs = repo.list_all_programs(session)
        computed = ori.compute_recommendations(answers, profile, programs)
        saved = False
        if user is not None:
            ori.save_result(session, user.id, answers, computed)
            saved = True
            set_flash("ori_save_ok")
    st.session_state["orientation_result"] = computed
    st.session_state["orientation_saved"] = saved
    st.session_state["orientation_done"] = True
    st.rerun()


heading(
    lang,
    tr("ori_title", lang),
    subtitle=tr("ori_intro", lang),
    kicker=tr("home_kicker", lang),
)
_run_questionnaire()
footer(lang)
