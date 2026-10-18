"""Fonctions utilitaires pures — NextStep Maroc.

Aucune dépendance à Streamlit ni à la base de données : ces fonctions sont
réutilisées par les services, les composants et les tests.
"""

from __future__ import annotations

import datetime as dt
import re
from typing import Any, Iterable, Optional

from database.models import (
    VERIFICATION_COMMUNITY,
    VERIFICATION_DEMO,
    VERIFICATION_OFFICIAL,
    VERIFICATION_PENDING,
    VERIFICATION_UNKNOWN,
)

# Métadonnées d'affichage des statuts de vérification : la clé de traduction
# est résolue dans utils/translations.py.
_VERIFICATION_META: dict[str, dict[str, str]] = {
    VERIFICATION_OFFICIAL: {"key": "status_official", "css": "ns-badge ns-badge-ok", "icon": "✔"},
    VERIFICATION_PENDING: {"key": "status_pending", "css": "ns-badge ns-badge-wait", "icon": "⏳"},
    VERIFICATION_UNKNOWN: {"key": "status_unknown", "css": "ns-badge ns-badge-unk", "icon": "?"},
    VERIFICATION_COMMUNITY: {"key": "status_community", "css": "ns-badge ns-badge-com", "icon": "👥"},
    VERIFICATION_DEMO: {"key": "status_demo", "css": "ns-badge ns-badge-demo", "icon": "🧪"},
}

_STATUS_ORDER = (VERIFICATION_OFFICIAL, VERIFICATION_PENDING, VERIFICATION_COMMUNITY, VERIFICATION_UNKNOWN, VERIFICATION_DEMO)


def verification_meta(status: Optional[str]) -> dict[str, str]:
    """Retourne ``{key, css, icon}`` pour un statut (défaut : inconnu)."""
    return dict(_VERIFICATION_META.get(status or VERIFICATION_UNKNOWN, _VERIFICATION_META[VERIFICATION_UNKNOWN]))


def is_official(status: Optional[str]) -> bool:
    return status == VERIFICATION_OFFICIAL


def status_rank(status: Optional[str]) -> int:
    try:
        return _STATUS_ORDER.index(status)  # type: ignore[arg-type]
    except ValueError:
        return len(_STATUS_ORDER)


def format_date(value: Optional[dt.date], lang: str = "fr", long: bool = False) -> str:
    """Formatage indépendant du système de locale (fr / ar / en)."""
    if value is None:
        return "—"
    if isinstance(value, dt.datetime):
        value = value.date()
    if lang == "en":
        pattern = "%B %d, %Y" if long else "%Y-%m-%d"
    else:  # fr et ar : JJ/MM/AAAA
        pattern = "%d/%m/%Y"
    try:
        return value.strftime(pattern)
    except ValueError:  # pragma: no cover - pattern constant
        return value.isoformat()


def format_datetime(value: Optional[dt.datetime], lang: str = "fr") -> str:
    if value is None:
        return "—"
    return f"{format_date(value.date(), lang)} {value.strftime('%H:%M')}"


def percentage(score: int, total: int) -> float:
    """Pourcentage arrondi à 1 décimale (0 si total nul)."""
    if total <= 0:
        return 0.0
    return round(100.0 * score / total, 1)


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def slugify(text: str, max_length: int = 80) -> str:
    text = (text or "").strip().lower()
    text = re.sub(r"[^\w\s\-]", "", text, flags=re.UNICODE)
    text = re.sub(r"[\s_]+", "-", text)
    return text[:max_length].strip("-")


def group_count(items: Iterable[Any], key_fn) -> dict[str, int]:
    """Compte les éléments par clé (utile pour les statistiques réelles)."""
    counts: dict[str, int] = {}
    for item in items:
        key = key_fn(item)
        key = key if key else "—"
        counts[key] = counts.get(key, 0) + 1
    return counts


def truncate(text: Optional[str], length: int = 160) -> str:
    text = text or ""
    if len(text) <= length:
        return text
    return text[: length - 1].rstrip() + "…"


def unique_sorted(values: Iterable[str]) -> list[str]:
    """Liste triée sans doublons, en ignorant les vides."""
    return sorted({(v or "").strip() for v in values if (v or "").strip()}, key=str.lower)


__all__ = [
    "clamp",
    "format_date",
    "format_datetime",
    "group_count",
    "is_official",
    "percentage",
    "slugify",
    "status_rank",
    "truncate",
    "unique_sorted",
    "verification_meta",
]
