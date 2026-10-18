"""Mise en page et éléments visuels — NextStep Maroc.

Principes :
* HTML produit par l'application uniquement, **toujours échappé** (``h``) pour
  éviter toute injection de contenu utilisateur ;
* styles centralisés dans ``assets/styles.css`` (classes métier ``ns-*``) ;
* mode RTL déclenché uniquement par des règles CSS ajoutées en arabe, sans
  manipulation DOM.
"""

from __future__ import annotations

import datetime as dt
import html
import pathlib
from typing import Any, Optional

import streamlit as st

from database.connection import BASE_DIR
from utils.helpers import verification_meta
from utils.translations import tr

CSS_PATH = BASE_DIR / "assets" / "styles.css"

RTL_OVERRIDES = """
<style>
html, body { direction: rtl; text-align: right; }
.ns-step { border-left: 0; border-right: 3px solid var(--ns-blue); padding: 0.15rem 1rem 0.15rem 0; }
.ns-rule { margin-left: auto; margin-right: 0; }
</style>
"""


def h(text: Any) -> str:
    """Échappe un texte pour toute insertion HTML."""
    if text is None:
        return ""
    return html.escape(str(text))


@st.cache_data(show_spinner=False)
def _load_css(path_str: str, version: float) -> str:
    """Charge le CSS (mis en cache, rechargé si le fichier change)."""
    try:
        return pathlib.Path(path_str).read_text(encoding="utf-8")
    except OSError:  # pragma: no cover - fichier obligatoire mais dégradation propre
        return ""


def inject_css(lang: str = "fr") -> None:
    """Injecte la feuille de style (et les ajustements RTL pour l'arabe)."""
    version = 0.0
    try:
        version = CSS_PATH.stat().st_mtime
    except OSError:  # pragma: no cover
        version = 0.0
    css = _load_css(str(CSS_PATH), version)
    extra = RTL_OVERRIDES if lang == "ar" else ""
    if css or extra:
        st.markdown(f"<style>{css}\n{extra}</style>", unsafe_allow_html=True)


def html_block(content: str) -> None:
    st.markdown(content, unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
# Titres et sections
# --------------------------------------------------------------------------- #


def heading(
    lang: str,
    title: str,
    subtitle: Optional[str] = None,
    kicker: Optional[str] = None,
    level: str = "ns-title",
) -> None:
    kicker_html = f'<div class="ns-kicker">{h(kicker)}</div>' if kicker else ""
    subtitle_html = f'<p class="ns-subtitle">{h(subtitle)}</p>' if subtitle else ""
    html_block(
        f"{kicker_html}<h1 class='{level}'>{h(title)}</h1>"
        f'<div class="ns-rule"></div>{subtitle_html}'
    )


def section_heading(lang: str, title: str, subtitle: Optional[str] = None) -> None:
    subtitle_html = f'<p class="ns-subtitle">{h(subtitle)}</p>' if subtitle else ""
    html_block(f'<div class="ns-section"><h2 class="ns-title-sm">{h(title)}</h2>{subtitle_html}</div>')


def badge(lang: str, status: str) -> str:
    """Badge HTML du statut de vérification (libellé traduit, échappé)."""
    meta = verification_meta(status)
    label = tr(meta["key"], lang)
    return f'<span class="{meta["css"]}">{meta["icon"]} {h(label)}</span>'


def status_badge(lang: str, status: str) -> None:
    html_block(badge(lang, status))


def unknown(lang: str) -> str:
    """Texte standard pour une information manquante (jamais de valeur inventée)."""
    return f"ℹ️ {tr('common_unknown', lang)}"


def notice(kind: str, content: str, unsafe: bool = False) -> None:
    """Encadré d'information : ``kind`` ∈ info | warn | demo."""
    css = {"info": "ns-notice ns-notice-info", "warn": "ns-notice ns-notice-warn", "demo": "ns-notice ns-notice-demo"}.get(kind, "ns-notice")
    body = content if unsafe else h(content)
    html_block(f'<div class="{css}">{body}</div>')


def stat_tile(value: Any, label: str) -> None:
    html_block(
        f'<div class="ns-stat"><div class="ns-stat-value">{h(value)}</div>'
        f'<span class="ns-stat-label">{h(label)}</span></div>'
    )


def progress_bar(percent: float, label: str = "") -> None:
    percent = max(0.0, min(100.0, float(percent)))
    label_html = f'<div class="ns-small ns-muted">{h(label)}</div>' if label else ""
    html_block(
        f'{label_html}<div class="ns-progress-track">'
        f'<div class="ns-progress-fill" style="width:{percent:.1f}%"></div></div>'
    )


# --------------------------------------------------------------------------- #
# Pied de page
# --------------------------------------------------------------------------- #


def footer(lang: str, year: Optional[int] = None) -> None:
    year = year or dt.date.today().year
    html_block(
        f"""
        <div class="ns-footer">
          <div class="ns-footer-cols">
            <div>
              <strong>{h(tr('footer_about_t', lang))}</strong><br>
              {h(tr('footer_about_d', lang))}
            </div>
            <div>
              <strong>{h(tr('footer_sources_t', lang))}</strong><br>
              {h(tr('footer_sources_d', lang))}
            </div>
            <div>
              <strong>{h(tr('footer_privacy_t', lang))}</strong><br>
              {h(tr('footer_privacy_d', lang))}
            </div>
            <div>
              <strong>{h(tr('footer_terms_t', lang))}</strong><br>
              {h(tr('footer_terms_d', lang))}
            </div>
          </div>
          <hr class="ns-divider">
          <div class="ns-small">
            {h(tr('footer_no_partnership', lang))}<br>
            {h(tr('footer_copyright', lang, year=year))}
          </div>
        </div>
        """
    )


__all__ = [
    "badge",
    "footer",
    "h",
    "heading",
    "html_block",
    "inject_css",
    "notice",
    "progress_bar",
    "section_heading",
    "stat_tile",
    "status_badge",
    "unknown",
]
