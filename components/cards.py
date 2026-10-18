"""Cartes et blocs d'affichage — NextStep Maroc.

Toutes les cartes reposent sur les conteneurs natifs de Streamlit
(``st.container(border=True)``) : responsive, accessible et sans HTML issu de
données utilisateur. Le HTML produit ici ne contient que du texte échappé.
"""

from __future__ import annotations

from typing import Any, Optional, Sequence

import streamlit as st

from components.layout import badge, h, html_block, progress_bar, unknown
from database.models import (
    CRITERION_AVERAGE,
    CRITERION_EXAM,
    CRITERION_OTHER,
    CRITERION_SERIES,
    DEADLINE_APPLICATION,
    DEADLINE_EXAM,
    DEADLINE_RESULT,
    Program,
    School,
)
from utils.helpers import format_date, percentage, truncate, verification_meta
from utils.translations import tr


# --------------------------------------------------------------------------- #
# Écoles
# --------------------------------------------------------------------------- #


def school_card(
    lang: str,
    school: School,
    *,
    favorite: bool = False,
    fav_key: Optional[str] = None,
    show_program_count: int = 1,
) -> bool:
    """Rend une fiche d'école. Retourne ``True`` si le bouton favori est cliqué."""
    clicked = False
    with st.container(border=True):
        meta = " · ".join(x for x in [school.city, school.domain, school.school_type] if x)
        html_block(f"<div class='ns-title-sm'>{h(school.name)}</div>")
        if meta:
            html_block(f"<div class='ns-small ns-muted'>{h(meta)}</div>")
        html_block(badge(lang, school.verification_status))
        if school.description:
            st.write(truncate(school.description, 240))

        programs = list(getattr(school, "programs", []) or [])
        if programs and show_program_count:
            st.caption(
                " · ".join(truncate(p.name, 60) for p in programs[:show_program_count])
                + (" …" if len(programs) > show_program_count else "")
            )

        left, right = st.columns([3, 1])
        with left:
            if school.official_url:
                st.markdown(f"[{tr('common_official_url', lang)} →]({school.official_url})")
            else:
                st.caption(unknown(lang))
            if school.last_verified_at:
                st.caption(
                    f"{tr('common_last_verified', lang)} : {format_date(school.last_verified_at, lang)}"
                )
        with right:
            if fav_key:
                label = tr("btn_remove_fav", lang) if favorite else tr("btn_add_fav", lang)
                if st.button(label, key=fav_key, use_container_width=True):
                    clicked = True
    return clicked


def program_card(
    lang: str,
    program: Program,
    *,
    favorite: bool = False,
    fav_key: Optional[str] = None,
    show_admission: bool = False,
) -> bool:
    """Rend une fiche formation (+ critères si ``show_admission``)."""
    clicked = False
    with st.container(border=True):
        head_l, head_r = st.columns([4, 1])
        with head_l:
            html_block(f"<div class='ns-title-sm'>{h(program.name)}</div>")
            meta = " · ".join(x for x in [program.degree_level, program.domain] if x)
            if meta:
                html_block(f"<div class='ns-small ns-muted'>{h(meta)}</div>")
        with head_r:
            html_block(badge(lang, program.verification_status))

        st.write(truncate(program.description, 400) or unknown(lang))

        cols = st.columns(3)
        with cols[0]:
            duration = (
                tr("sch_years", lang, years=int(program.duration_years))
                if program.duration_years
                else unknown(lang)
            )
            st.markdown(f"**{tr('sch_program_duration', lang)}**  \n{duration}")
        with cols[1]:
            fees = (
                tr("sch_fees_value", lang, amount=f"{program.tuition_fees_mad:,.0f}".replace(",", " "))
                if program.tuition_fees_mad
                else unknown(lang)
            )
            st.markdown(f"**{tr('sch_program_fees', lang)}**  \n{fees}")
        with cols[2]:
            st.markdown(
                f"**{tr('sch_program_language', lang)}**  \n{program.teaching_language or unknown(lang)}"
            )
        if program.tuition_note:
            st.caption(program.tuition_note)

        if fav_key:
            label = tr("btn_remove_fav", lang) if favorite else tr("btn_add_fav", lang)
            if st.button(label, key=fav_key, use_container_width=True):
                clicked = True

        if show_admission:
            admission_section(lang, program)
    return clicked


# --------------------------------------------------------------------------- #
# Critères d'admission
# --------------------------------------------------------------------------- #

_CRITERION_KEYS = {
    CRITERION_SERIES: "sch_criteria_series",
    CRITERION_AVERAGE: "sch_criteria_average",
    CRITERION_EXAM: "sch_criteria_exam",
    CRITERION_OTHER: "sch_criteria_other",
}


def _criterion_value(criterion) -> str:
    if criterion.criterion_type == CRITERION_SERIES:
        values = criterion.value if isinstance(criterion.value, list) else [criterion.value]
        return " · ".join(str(v) for v in values)
    if criterion.criterion_type == CRITERION_AVERAGE:
        try:
            return f"{float(criterion.value):g} / 20"
        except (TypeError, ValueError):
            return str(criterion.value)
    return str(criterion.value)


def admission_section(lang: str, program: Program) -> None:
    """Affiche les critères d'accès d'une formation, avec source et statut."""
    st.markdown(f"**{tr('sch_admission', lang)}**")
    rules = list(getattr(program, "admission_rules", []) or [])
    if not rules:
        st.info(tr("sch_no_admission", lang))
        return

    for rule in rules:
        html_block(badge(lang, rule.verification_status))
        if rule.label:
            st.caption(rule.label)
        criteria = list(getattr(rule, "criteria", []) or [])
        if not criteria:
            st.caption(unknown(lang))
        for criterion in criteria:
            required = (
                tr("sch_criteria_required", lang)
                if criterion.is_required
                else tr("sch_criteria_optional", lang)
            )
            type_label = tr(_CRITERION_KEYS.get(criterion.criterion_type, "sch_criteria_other"), lang)
            description_html = (
                f"<div class='ns-muted ns-small'>{h(criterion.description)}</div>"
                if criterion.description
                else ""
            )
            html_block(
                f"<div class='ns-small' style='margin:.35rem 0'>"
                f"<b>{h(type_label)}</b> — <code>{h(_criterion_value(criterion))}</code> "
                f"({h(required)}) {badge(lang, criterion.verification_status)}"
                f"{description_html}</div>"
            )
        source_bits = []
        if rule.source_name:
            source_bits.append(f"{tr('common_source', lang)} : {rule.source_name}")
        if rule.source_url:
            source_bits.append(f"[{rule.source_url}]({rule.source_url})")
        if rule.verified_at:
            source_bits.append(
                f"{tr('common_last_verified', lang)} : {format_date(rule.verified_at, lang)}"
            )
        if source_bits:
            st.caption(" — ".join(source_bits))


# --------------------------------------------------------------------------- #
# Échéances
# --------------------------------------------------------------------------- #

_DEADLINE_KEYS = {
    DEADLINE_APPLICATION: "dl_type_candidature",
    DEADLINE_EXAM: "dl_type_concours",
    DEADLINE_RESULT: "dl_type_resultat",
}


def deadline_card(lang: str, deadline, context_label: str = "") -> None:
    with st.container(border=True):
        head_l, head_r = st.columns([3, 1])
        with head_l:
            html_block(f"<div style='font-weight:700'>{h(deadline.title)}</div>")
            if context_label:
                st.caption(context_label)
        with head_r:
            html_block(badge(lang, deadline.verification_status))

        if deadline.event_date:
            st.markdown(f"**{format_date(deadline.event_date, lang, long=(lang == 'en'))}**")
        else:
            st.caption(unknown(lang))

        st.caption(
            f"{tr(_DEADLINE_KEYS.get(deadline.deadline_type, 'dl_type_autre'), lang)}"
        )
        if deadline.source_name:
            line = f"{tr('common_source', lang)} : {deadline.source_name}"
            if deadline.source_url:
                line += f" — [{deadline.source_url}]({deadline.source_url})"
            st.caption(line)
        elif deadline.verification_status != "official_verified":
            st.caption(unknown(lang))


# --------------------------------------------------------------------------- #
# Résultats d'orientation
# --------------------------------------------------------------------------- #


def pathway_card(lang: str, pathway: dict[str, Any], rank: int) -> None:
    """Piste de parcours : indice d'intérêt (jamais présenté comme probabilité)."""
    with st.container(border=True):
        top_l, top_r = st.columns([3, 1])
        with top_l:
            html_block(
                f"<div class='ns-title-sm'>{rank}. {h(tr(pathway['label_key'], lang))}</div>"
            )
        with top_r:
            html_block(
                f"<div style='text-align:right;font-weight:800;color:var(--ns-blue);font-size:1.4rem'>"
                f"{pathway['index']}<span class='ns-small ns-muted'> /100</span></div>"
            )
        st.caption(tr("ori_score_label", lang))
        progress_bar(pathway["index"])

        reasons = list(pathway.get("reasons", []))
        if reasons:
            st.markdown(f"**{tr('ori_reasons', lang)}**")
            # Les signaux les plus forts d'abord (explication lisible).
            for reason in sorted(reasons, key=lambda r: -r["weight"])[:6]:
                question = tr(reason["question"], lang) if _is_translatable(reason["question"]) else reason["question"]
                option = tr(reason["option"], lang) if _is_translatable(reason["option"]) else reason["option"]
                st.markdown(
                    f"- {tr('ori_reason_line', lang, question=question, option=option, weight=reason['weight'])}"
                )


def _is_translatable(key: str) -> bool:
    from utils.translations import T

    return key in T


def match_status_badge(lang: str, status: str) -> str:
    css = {
        "ok": "ns-badge ns-badge-ok",
        "ko": "ns-badge ns-badge-ko",
        "unknown": "ns-badge ns-badge-wait",
        "no_rule": "ns-badge ns-badge-unk",
    }.get(status, "ns-badge ns-badge-unk")
    label = {
        "ok": tr("ori_match_ok", lang),
        "ko": tr("ori_match_ko", lang),
        "unknown": tr("ori_match_unknown", lang),
        "no_rule": tr("ori_match_no_rule", lang),
    }.get(status, status)
    return f"<span class='{css}'>{h(label)}</span>"


def match_card(lang: str, match: dict[str, Any]) -> None:
    """Compatibilité d'une formation : critères connus uniquement, pas de probabilité."""
    with st.container(border=True):
        html_block(match_status_badge(lang, match["status"]))
        html_block(f"<div class='ns-title-sm'>{h(match['program_name'])}</div>")
        if match.get("school_name"):
            st.caption(match["school_name"])
        for check in match.get("checks", []):
            st.markdown(f"- {tr(check['key'], lang, **check.get('params', {}))}")
        if match["status"] == "no_rule":
            st.caption(tr("ori_match_no_rule", lang))


# --------------------------------------------------------------------------- #
# QCM
# --------------------------------------------------------------------------- #


def quiz_card(lang: str, quiz, attempts_for_quiz: int = 0, best: Optional[float] = None) -> bool:
    """Carte d'un QCM. Retourne ``True`` si « Commencer » est cliqué."""
    started = False
    with st.container(border=True):
        head_l, head_r = st.columns([3, 1])
        with head_l:
            html_block(f"<div class='ns-title-sm'>{h(quiz.subject)}</div>")
            st.write(quiz.title)
        with head_r:
            html_block(badge(lang, quiz.validation_status))
        if quiz.description:
            st.caption(truncate(quiz.description, 200))
        meta_bits = [
            f"{len(quiz.questions)} questions",
            quiz.difficulty or "",
            f"{tr('common_language', lang)} : {quiz.language}",
        ]
        st.caption(" · ".join(b for b in meta_bits if b))
        if quiz.provenance:
            st.caption(f"{tr('prep_provenance', lang)} : {truncate(quiz.provenance, 160)}")
        cols = st.columns([2, 2, 2])
        with cols[0]:
            if attempts_for_quiz:
                st.caption(f"{tr('prep_attempts_count', lang)} : {attempts_for_quiz}")
        with cols[1]:
            if best is not None:
                st.caption(f"{tr('prep_best', lang)} : {best:g} %")
        with cols[2]:
            if st.button(tr("prep_start", lang), key=f"start_quiz_{quiz.id}", use_container_width=True):
                started = True
    return started


# --------------------------------------------------------------------------- #
# Ressources
# --------------------------------------------------------------------------- #


def resource_card(lang: str, resource, *, report_key: Optional[str] = None) -> bool:
    """Carte de ressource. Retourne ``True`` si « Signaler » est cliqué."""
    reported = False
    with st.container(border=True):
        head_l, head_r = st.columns([4, 1])
        with head_l:
            html_block(f"<div class='ns-title-sm'>{h(resource.title)}</div>")
        with head_r:
            if resource.is_demo:
                html_block(badge(lang, "demo"))
            elif resource.status == "published":
                html_block(badge(lang, "community"))
        if resource.description:
            st.write(resource.description)
        st.caption(
            " · ".join(
                b
                for b in [
                    resource.category or "",
                    f"{tr('common_language', lang)} : {resource.language}",
                    resource.author_name or "",
                    f"{tr('res_label_submitted_at', lang)} : {format_date(resource.created_at, lang)}",
                ]
                if b
            )
        )
        if resource.content:
            with st.expander(tr("btn_details", lang)):
                st.write(resource.content)
        if report_key and st.button(tr("btn_report", lang), key=report_key):
            reported = True
    return reported


__all__ = [
    "admission_section",
    "deadline_card",
    "match_card",
    "match_status_badge",
    "pathway_card",
    "program_card",
    "quiz_card",
    "resource_card",
    "school_card",
]
