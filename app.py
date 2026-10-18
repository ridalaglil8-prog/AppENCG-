"""NextStep Maroc — point d'entrée de l'application Streamlit.

Ce fichier joue deux rôles (API ``st.navigation`` de Streamlit ≥ 1.36) :

1. **Cadre commun** : configuration, initialisation de la base, styles,
   barre latérale (marque, langue, authentification) et navigation — il est
   exécuté à **chaque** rerun, donc la barre latérale persiste sur toutes les
   pages ;
2. **Page d'accueil** : la fonction :func:`home` est enregistrée comme page
   par défaut de la navigation.

Lancement :
    streamlit run app.py
"""

from __future__ import annotations

import streamlit as st

from components.layout import (
    footer,
    h,
    heading,
    html_block,
    inject_css,
    notice,
    section_heading,
    stat_tile,
)
from components.navigation import (
    build_navigation,
    current_language,
    current_user,
    ensure_runtime,
    flash_messages,
    render_sidebar,
    session_defaults,
)
from database import repositories as repo
from database.connection import db_session
from services import school_service

# --------------------------------------------------------------------------- #
# Cadre commun (doit rester au niveau module de l'entrypoint)
# --------------------------------------------------------------------------- #

st.set_page_config(
    page_title="NextStep Maroc — Orientation après le bac",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)

ensure_runtime()
session_defaults()
_LANG = current_language()
inject_css(_LANG)

# NOTE : ``build_navigation`` + ``render_sidebar`` sont appelés plus bas, après
# la définition de la page d'accueil, mais **avant** ``navigation.run()`` :
# les pages doivent être enregistrées par ``st.Page``/``st.navigation`` AVANT
# tout ``st.page_link`` de la barre latérale (sinon Streamlit lève
# ``StreamlitPageNotFoundError``).


@st.cache_data(ttl=60, show_spinner=False)
def _stats_cached(database_url: str) -> dict:
    """Statistiques réelles (mises en cache 60 s, clé = base utilisée)."""
    with db_session() as session:
        return repo.compute_stats(session)


def _stats() -> dict:
    from database.connection import get_database

    try:
        return _stats_cached(get_database().url)
    except Exception:  # pragma: no cover - base indisponible
        return {}


# --------------------------------------------------------------------------- #
# Page d'accueil
# --------------------------------------------------------------------------- #


def home() -> None:
    lang = current_language()
    user = current_user()
    stats = _stats()

    # --- Héros -------------------------------------------------------------
    html_block(
        f"""
        <div class="ns-hero">
          <div class="ns-flag">🎓 {h("Maroc · Baccalauréat · Concours")}</div>
          <h1>{h("NextStep Maroc")}</h1>
          <div class="ns-lead">{h(_HERO_TEXT[lang])}</div>
        </div>
        """
    )

    cta_l, cta_r, cta_gap = st.columns([2, 2, 1])
    with cta_l:
        st.page_link(
            "pages/1_Orientation.py",
            label=_T("btn_start", lang),
            icon="🧭",
            use_container_width=True,
        )
    with cta_r:
        st.page_link(
            "pages/2_Ecoles_Formations.py",
            label=_T("btn_catalog", lang),
            icon="🎓",
            use_container_width=True,
        )

    notice("demo", _T("common_demo_notice", lang))

    # --- Fonctionnalités ---------------------------------------------------
    section_heading(lang, _T("home_features_title", lang), _T("home_features_text", lang))
    features = [
        ("🗂️", "feat1_t", "feat1_d", False),
        ("🧭", "feat2_t", "feat2_d", True),
        ("✅", "feat3_t", "feat3_d", False),
        ("📝", "feat4_t", "feat4_d", True),
        ("⭐", "feat5_t", "feat5_d", False),
        ("🔍", "feat6_t", "feat6_d", False),
    ]
    for row_start in range(0, len(features), 3):
        cols = st.columns(3)
        for col, (icon, title_key, desc_key, green) in zip(cols, features[row_start : row_start + 3]):
            with col, st.container(border=True):
                html_block(
                    f'<div class="ns-icon{" ns-icon-green" if green else ""}">{icon}</div>'
                    f'<div style="font-weight:700;color:var(--ns-navy)">{h(_T(title_key, lang))}</div>'
                    f'<p class="ns-small ns-muted" style="margin:.35rem 0 0">{h(_T(desc_key, lang))}</p>'
                )

    # --- Parcours ----------------------------------------------------------
    section_heading(lang, _T("home_how_title", lang), _T("home_how_text", lang))
    html_block(f'<div class="ns-grid">{_render_steps(lang)}</div>')

    # --- Statistiques réelles --------------------------------------------
    section_heading(lang, _T("home_stats_title", lang), _T("home_stats_note", lang))
    stat_cols = st.columns(5)
    entries = [
        (stats.get("schools", 0), "stat_schools"),
        (stats.get("programs", 0), "stat_programs"),
        (stats.get("quizzes", 0), "stat_quizzes"),
        (stats.get("questions", 0), "stat_questions"),
        (stats.get("users", 0), "stat_users"),
    ]
    for col, (value, key) in zip(stat_cols, entries):
        with col:
            stat_tile(value, _T(key, lang))

    # --- Aperçu catalogue (données réelles) -------------------------------
    section_heading(lang, _T("nav_schools", lang), _T("sch_intro", lang))
    try:
        with db_session() as session:
            featured = school_service.search_catalog(session)[:3]
            fav_ids: set[int] = set()
    except Exception:  # pragma: no cover
        featured = []
    if featured:
        cols = st.columns(3)
        for col, school in zip(cols, featured):
            with col:
                _school_teaser(school, lang)
    else:
        st.info(_T("sch_no_result", lang))

    if not user:
        html_block(
            f'<div class="ns-notice ns-notice-info"><b>{h(_T("dash_guest_title", lang))}</b> — '
            f'{h(_T("dash_guest_text", lang))}</div>'
        )

    footer(lang)


_HERO_TEXT = {
    "fr": "Découvre les écoles et formations accessibles après le bac, comprends les critères d'admission et prépare les concours — avec des informations sourcées, datées et vérifiées, gratuites et en trois langues.",
    "ar": "اكتشف المدارس والتكوينات المتاحة بعد البكالوريا، وافهم شروط القبول واستعد للمباريات — بمعلومات موثقة ومؤرخة ومُتحقق منها، مجانية بثلاث لغات.",
    "en": "Discover schools and programs available after the bac, understand admission criteria and prepare for exams — with sourced, dated and verified information, free and in three languages.",
}


def _render_steps(lang: str) -> str:
    blocks = []
    for index in range(1, 5):
        blocks.append(
            '<div class="ns-step">'
            f'<div class="ns-step-num">{index:02d}</div>'
            f'<h4>{h(_T(f"how{index}_t", lang))}</h4>'
            f'<p>{h(_T(f"how{index}_d", lang))}</p>'
            "</div>"
        )
    return "".join(blocks)


def _school_teaser(school, lang: str) -> None:
    from components.layout import badge

    with st.container(border=True):
        html_block(f"<div style='font-weight:700;color:var(--ns-navy)'>{h(school.name)}</div>")
        html_block(
            f"<div class='ns-small ns-muted'>{h(' · '.join(x for x in [school.city, school.domain] if x))}</div>"
        )
        html_block(badge(lang, school.verification_status))
        if school.official_url:
            st.markdown(f"[{_T('common_official_url', lang)} →]({school.official_url})")


def _T(key: str, lang: str) -> str:
    from utils.translations import tr

    return tr(key, lang)


# --------------------------------------------------------------------------- #
# Routage
# --------------------------------------------------------------------------- #

# Ordre important :
#   1. enregistrement des pages (st.navigation) — requis par st.page_link ;
#   2. barre latérale commune (marque, langue, authentification) ;
#   3. exécution de la page sélectionnée.
navigation = build_navigation(_LANG, home, current_user())
render_sidebar(_LANG)
flash_messages(_LANG)
navigation.run()
