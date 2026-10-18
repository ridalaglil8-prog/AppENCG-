"""Service du catalogue (écoles, formations, favoris, échéances).

Règles gérées ici :
* recherche et filtrage délégués aux repositories (ORM, requêtes paramétrées) ;
* favoris idempotents : ajouter deux fois ne crée pas de doublon ;
* échéances séparées en « confirmées » (statut officiel vérifié **et** date
  renseignée) et « non vérifiées » ; aucune date n'est inventée.
"""

from __future__ import annotations

import datetime as dt
from typing import Any, Optional

from sqlalchemy.orm import Session

from database import repositories as repo
from database.models import FAV_PROGRAM, FAV_SCHOOL, Deadline, Favorite, Program, School
from utils.exceptions import BusinessValidationError, NotFoundError


# --------------------------------------------------------------------------- #
# Catalogue
# --------------------------------------------------------------------------- #


def search_catalog(session: Session, **filters: Any) -> list[School]:
    """Recherche filtrée ; les clés inconnues sont ignorées proprement."""
    allowed = {
        "name",
        "city",
        "domain",
        "degree",
        "school_type",
        "series",
        "active_only",
        "include_demo",
    }
    return repo.search_schools(session, **{k: v for k, v in filters.items() if k in allowed})


def catalog_facets(session: Session) -> dict[str, list[str]]:
    """Valeurs disponibles pour chaque filtre (issues de la base, pas codées en dur)."""
    return {
        "cities": repo.list_cities(session),
        "domains": repo.list_domains(session),
        "school_types": repo.list_school_types(session),
        "degrees": repo.list_degree_levels(session),
        "series": repo.series_with_official_rules(session),
    }


def get_school_detail(session: Session, school_id: int) -> School:
    school = repo.get_school(session, school_id)
    if school is None or not school.is_active:
        raise NotFoundError("error_not_found")
    return school


def list_programs(session: Session, school_id: int) -> list[Program]:
    return repo.list_programs_for_school(session, school_id)


def get_program_detail(session: Session, program_id: int) -> Program:
    program = repo.get_program(session, program_id)
    if program is None or not program.is_active:
        raise NotFoundError("error_not_found")
    return program


# --------------------------------------------------------------------------- #
# Favoris
# --------------------------------------------------------------------------- #


def add_favorite_school(session: Session, user_id: int, school_id: int) -> Favorite:
    get_school_detail(session, school_id)  # existence / activation
    existing = repo.get_favorite(session, user_id, FAV_SCHOOL, school_id)
    if existing is not None:
        return existing
    favorite = Favorite(user_id=user_id, target_type=FAV_SCHOOL, school_id=school_id)
    session.add(favorite)
    session.flush()
    repo.add_audit_log(
        session,
        actor_id=user_id,
        action="favorite.add",
        entity_type="school",
        entity_id=school_id,
        detail={"target": "school"},
    )
    return favorite


def add_favorite_program(session: Session, user_id: int, program_id: int) -> Favorite:
    program = get_program_detail(session, program_id)
    existing = repo.get_favorite(session, user_id, FAV_PROGRAM, program_id)
    if existing is not None:
        return existing
    favorite = Favorite(
        user_id=user_id, target_type=FAV_PROGRAM, program_id=program_id, school_id=program.school_id
    )
    session.add(favorite)
    session.flush()
    repo.add_audit_log(
        session,
        actor_id=user_id,
        action="favorite.add",
        entity_type="program",
        entity_id=program_id,
        detail={"target": "program"},
    )
    return favorite


def remove_favorite_school(session: Session, user_id: int, school_id: int) -> bool:
    return _remove_favorite(session, user_id, FAV_SCHOOL, school_id)


def remove_favorite_program(session: Session, user_id: int, program_id: int) -> bool:
    return _remove_favorite(session, user_id, FAV_PROGRAM, program_id)


def _remove_favorite(session: Session, user_id: int, target_type: str, target_id: int) -> bool:
    favorite = repo.get_favorite(session, user_id, target_type, target_id)
    if favorite is None:
        return False
    session.delete(favorite)
    session.flush()
    repo.add_audit_log(
        session,
        actor_id=user_id,
        action="favorite.remove",
        entity_type=target_type,
        entity_id=target_id,
        detail={"target": target_type},
    )
    return True


def is_favorite(session: Session, user_id: Optional[int], target_type: str, target_id: int) -> bool:
    if not user_id:
        return False
    return repo.get_favorite(session, user_id, target_type, target_id) is not None


def favorite_school_ids(session: Session, user_id: Optional[int]) -> set[int]:
    if not user_id:
        return set()
    return {f.school_id for f in repo.list_favorites(session, user_id) if f.school_id}


def list_favorites(session: Session, user_id: int) -> list[Favorite]:
    return repo.list_favorites(session, user_id)


def favorite_counts(session: Session, user_id: int) -> dict[str, int]:
    favorites = repo.list_favorites(session, user_id)
    return {
        "schools": sum(1 for f in favorites if f.target_type == FAV_SCHOOL),
        "programs": sum(1 for f in favorites if f.target_type == FAV_PROGRAM),
        "total": len(favorites),
    }


# --------------------------------------------------------------------------- #
# Échéances
# --------------------------------------------------------------------------- #


def confirmed_deadlines(session: Session, from_date: Optional[dt.date] = None, limit: int = 20) -> list[Deadline]:
    return repo.list_deadlines(session, confirmed_only=True, from_date=from_date, limit=limit)


def unverified_deadlines(session: Session, limit: int = 50) -> list[Deadline]:
    rows = repo.list_deadlines(session, confirmed_only=False, limit=limit * 3)
    return [row for row in rows if row.verification_status != "official_verified"][:limit]


def all_deadlines(session: Session, limit: int = 100) -> list[Deadline]:
    return repo.list_deadlines(session, confirmed_only=False, limit=limit)


def deadline_context(session: Session, deadline: Deadline) -> dict[str, str]:
    """Rattachement lisible d'une échéance (école / formation / « — »)."""
    if deadline.program is not None:
        return {
            "label": deadline.program.name,
            "school": deadline.program.school.name if deadline.program.school else "",
        }
    if deadline.school is not None:
        return {"label": deadline.school.name, "school": ""}
    return {"label": "", "school": ""}


__all__ = [
    "add_favorite_program",
    "add_favorite_school",
    "all_deadlines",
    "catalog_facets",
    "confirmed_deadlines",
    "deadline_context",
    "favorite_counts",
    "favorite_school_ids",
    "get_program_detail",
    "get_school_detail",
    "is_favorite",
    "list_favorites",
    "list_programs",
    "remove_favorite_program",
    "remove_favorite_school",
    "search_catalog",
    "unverified_deadlines",
]
