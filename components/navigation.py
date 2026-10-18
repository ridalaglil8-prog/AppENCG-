"""Navigation, état de session et barre latérale — NextStep Maroc.

Responsabilités :
* initialiser la base de façon idempotente (et le seed de démonstration si
  ``NEXTSTEP_SEED_DEMO_DATA`` est actif) ;
* gérer la session Streamlit (langue, utilisateur connecté) ;
* rendre la barre latérale commune à toutes les pages (marque, langue,
  authentification) ;
* construire la navigation avec des libellés **traduits** (``st.navigation``).

Limites documentées : ``st.session_state`` est de l'état de processus, pas une
frontière de sécurité. Chaque opération sensible repasse par les services
(``ensure_role``), qui contrôlent réellement le rôle en base.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

import streamlit as st

from components.layout import h, html_block, inject_css, notice
from database import repositories as repo
from database.connection import db_session, init_database
from database.models import ROLE_ADMIN, ROLE_MODERATOR, User
from database.seed import seed_if_requested
from utils.translations import LANGUAGES, tr

_SEEDED = False


# --------------------------------------------------------------------------- #
# Runtime (base de données + session)
# --------------------------------------------------------------------------- #


def ensure_runtime() -> None:
    """Initialise la base et, si demandé, le jeu de démonstration. Idempotent."""
    global _SEEDED
    init_database()
    if not _SEEDED:
        try:
            seed_if_requested()
        except Exception as exc:  # pragma: no cover - seed optionnel
            st.warning(f"Seed de démonstration impossible : {exc}")
        _SEEDED = True


def session_defaults() -> None:
    st.session_state.setdefault("lang", "fr")
    st.session_state.setdefault("user_id", None)
    st.session_state.setdefault("orientation_answers", {})
    st.session_state.setdefault("orientation_step", 0)
    st.session_state.setdefault("quiz_answers", {})  # {quiz_id: {question_id: option_id}}
    st.session_state.setdefault("quiz_corrections", {})  # {quiz_id: [corrections]}


def current_language() -> str:
    lang = st.session_state.get("lang", "fr")
    return lang if lang in LANGUAGES else "fr"


def set_language(lang: str) -> None:
    if lang not in LANGUAGES:
        return
    st.session_state["lang"] = lang
    user = st.session_state.get("current_user")
    if user is not None:
        try:
            with db_session() as session:
                row = repo.get_user(session, user.id)
                if row is not None and row.language != lang:
                    row.language = lang
                    session.flush()
        except Exception:  # pragma: no cover - la préférence reste en session
            pass


def current_user() -> Optional[User]:
    """Utilisateur courant (rechargé depuis la base à chaque appel)."""
    user_id = st.session_state.get("user_id")
    if not user_id:
        st.session_state["current_user"] = None
        return None
    try:
        with db_session() as session:
            user = repo.get_user(session, int(user_id))
    except Exception:  # pragma: no cover
        st.session_state["user_id"] = None
        st.session_state["current_user"] = None
        return None
    if user is None or not user.is_active:
        # Compte supprimé ou désactivé entre deux reruns : on referme la session.
        st.session_state["user_id"] = None
        st.session_state["current_user"] = None
        return None
    st.session_state["current_user"] = user
    return user


def login_user(user: User) -> None:
    st.session_state["user_id"] = user.id
    st.session_state["user_email"] = user.email
    st.session_state["user_role"] = user.role
    st.session_state["lang"] = user.language if user.language in LANGUAGES else current_language()
    st.session_state["current_user"] = user


def logout_user() -> None:
    for key in ("user_id", "user_email", "user_role", "current_user"):
        st.session_state.pop(key, None)
    st.session_state["lang"] = current_language()


def _on_logout() -> None:
    logout_user()
    set_flash("msg_logout_ok")


def set_flash(key: str, **params: Any) -> None:
    st.session_state["flash"] = {"key": key, "params": params}


def pop_flash() -> Optional[dict]:
    return st.session_state.pop("flash", None)


def flash_messages(lang: str) -> None:
    flash = pop_flash()
    if flash:
        st.success(tr(flash["key"], lang, **flash.get("params", {})))


def is_staff(user: Optional[User]) -> bool:
    return bool(user is not None and user.role in (ROLE_MODERATOR, ROLE_ADMIN))


# --------------------------------------------------------------------------- #
# Barre latérale
# --------------------------------------------------------------------------- #


def render_sidebar(lang: str) -> Optional[User]:
    """Barre latérale commune (à appeler **une fois** par exécution de l'app)."""
    with st.sidebar:
        html_block(
            '<div class="ns-brand">NextStep <span class="ns-brand-accent">Maroc</span></div>'
            f'<div class="ns-small ns-muted">{h(tr("app_tagline", lang))}</div>'
            f'<hr class="ns-divider">'
        )

        codes = list(LANGUAGES)
        current = current_language()
        chosen = st.selectbox(
            tr("lang_label", lang),
            options=codes,
            index=codes.index(current) if current in codes else 0,
            format_func=lambda code: LANGUAGES[code],
            key="ui_language",
        )
        if chosen != current:
            set_language(chosen)
            st.rerun()

        st.markdown("")
        user = current_user()
        if user is None:
            st.page_link(
                "pages/5_Mon_Profil.py",
                label=tr("btn_login", lang),
                icon="👤",
            )
            st.page_link(
                "pages/5_Mon_Profil.py",
                label=tr("btn_register", lang),
                icon="➕",
            )
        else:
            role_key = {
                ROLE_ADMIN: "role_administrateur",
                ROLE_MODERATOR: "role_moderateur",
            }.get(user.role, "role_candidat")
            role_label = tr(role_key, lang)
            html_block(
                f'<div class="ns-card ns-card-tight">'
                f'<div class="ns-small ns-muted">{h(tr("nav_profile", lang))}</div>'
                f'<div style="font-weight:700">{h(user.email)}</div>'
                f'<span class="ns-badge ns-badge-com">{h(role_label)}</span></div>'
            )
            st.button(tr("btn_logout", lang), key="sidebar_logout", on_click=_on_logout, use_container_width=True)

        st.markdown("")
        notice("demo", tr("common_demo_notice", lang))
    return user


# --------------------------------------------------------------------------- #
# Pages
# --------------------------------------------------------------------------- #


def prepare_page() -> str:
    """Appelé en tête de chaque page : runtime + défauts de session, sans sortie."""
    ensure_runtime()
    session_defaults()
    return current_language()


def build_navigation(lang: str, home_page: Callable[[], None], user: Optional[User]):
    """Construit la navigation (libellés traduits, page d'administration masquée)."""
    pages = [
        st.Page(home_page, title=tr("nav_home", lang), icon="🏠", default=True),
        st.Page("pages/0_Tableau_de_bord.py", title=tr("nav_dashboard", lang), icon="📊"),
        st.Page("pages/1_Orientation.py", title=tr("nav_orientation", lang), icon="🧭"),
        st.Page("pages/2_Ecoles_Formations.py", title=tr("nav_schools", lang), icon="🎓"),
        st.Page("pages/3_Preparation_Concours.py", title=tr("nav_prep", lang), icon="📚"),
        st.Page("pages/4_Mes_Favoris.py", title=tr("nav_favorites", lang), icon="❤️"),
        st.Page("pages/5_Mon_Profil.py", title=tr("nav_profile", lang), icon="👤"),
    ]
    if is_staff(user):
        pages.append(st.Page("pages/6_Administration.py", title=tr("nav_admin", lang), icon="🛠️"))
    return st.navigation(pages, position="sidebar", expanded=True)


__all__ = [
    "build_navigation",
    "current_language",
    "current_user",
    "ensure_runtime",
    "flash_messages",
    "is_staff",
    "login_user",
    "logout_user",
    "pop_flash",
    "prepare_page",
    "render_sidebar",
    "session_defaults",
    "set_flash",
    "set_language",
]
