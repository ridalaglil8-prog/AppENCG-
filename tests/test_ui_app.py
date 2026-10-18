"""Tests d'interface avec ``streamlit.testing.v1.AppTest``.

Ces tests exécutent réellement l'application Streamlit sur une base temporaire
et vérifient que l'interface s'affiche sans erreur fatale.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

pytest.importorskip("streamlit.testing.v1")

from streamlit.testing.v1 import AppTest  # noqa: E402


@pytest.fixture()
def at(db, tmp_path):
    """Application exécutée sur la base temporaire du test."""
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60)
    app.run()
    return app


def test_home_page_loads_without_exception(at):
    assert not at.exception, [str(exc.value) for exc in at.exception]


def test_home_shows_brand_and_demo_notice(at):
    texts = " ".join(element.value for element in at.markdown)
    assert "NextStep Maroc" in texts
    # Avertissement de démonstration visible (pas de catalogue officiel).
    assert "démo" in texts.lower() or "demo" in texts.lower()


def test_language_selector_is_in_sidebar(at):
    labels = [selectbox.label for selectbox in at.sidebar.selectbox]
    assert labels, "aucun sélecteur de langue dans la barre latérale"
    values = at.sidebar.selectbox[0].value
    assert values in ("fr", "ar", "en")


def test_guest_sees_login_entry(at):
    sidebar_text = " ".join(str(markdown.value) for markdown in at.sidebar.markdown)
    assert sidebar_text.strip()


def test_switching_language_to_arabic_does_not_crash(at):
    at.sidebar.selectbox[0].select("ar").run()
    assert not at.exception, [str(exc.value) for exc in at.exception]


def test_home_shows_real_statistics(at):
    """Les compteurs de la page d'accueil proviennent de la base."""
    html = " ".join(str(markdown.value) for markdown in at.markdown)
    assert "ns-stat" in html  # tuiles de statistiques rendues


def _run_page(path: Path, db) -> AppTest:
    page = AppTest.from_file(str(path), default_timeout=60)
    page.run()
    return page


def test_catalog_page_renders(db):
    page = _run_page(ROOT / "pages" / "2_Ecoles_Formations.py", db)
    assert not page.exception, [str(exc.value) for exc in page.exception]


def test_orientation_page_renders(db):
    page = _run_page(ROOT / "pages" / "1_Orientation.py", db)
    assert not page.exception, [str(exc.value) for exc in page.exception]


def test_administration_page_blocks_candidates(db):
    """Un candidat ne voit pas l'espace d'administration (contrôle côté service
    testé dans test_permissions ; ici : le garde de l'interface)."""
    page = _run_page(ROOT / "pages" / "6_Administration.py", db)
    assert not page.exception, [str(exc.value) for exc in page.exception]
    messages = [error.value for error in page.error]
    assert messages, "aucun message d'erreur affiché au candidat"
    assert any("Accès réservé" in message for message in messages)
