"""Service des ressources communautaires et des signalements.

Aucune ressource soumise par un utilisateur n'est publiée automatiquement :
elle passe obligatoirement par ``pending`` puis par une décision de modération
(``published`` / ``rejected`` / ``to_revise`` / ``archived``).

Les permissions sont vérifiées **dans ce module** (et non en masquant des
boutons dans l'interface) via ``services.auth_service.ensure_role``.
"""

from __future__ import annotations

from typing import Optional

from pydantic import ValidationError
from sqlalchemy.orm import Session

from database import repositories as repo
from database.models import (
    REPORT_DISMISSED,
    REPORT_OPEN,
    REPORT_RESOLVED,
    RESOURCE_PENDING,
    RESOURCE_PUBLISHED,
    Report,
    Resource,
    User,
    utcnow,
)
from utils.exceptions import BusinessValidationError, NotFoundError, PermissionDenied
from utils.validators import ResourceInput, ResourceStatusInput, ReportInput

STAFF_ROLES = ("moderateur", "administrateur")
RESOURCE_STATUS_VALUES = (
    "draft",
    "pending",
    "published",
    "rejected",
    "to_revise",
    "archived",
)


def submit_resource(session: Session, user_id: int, data: dict) -> Resource:
    """Dépose une ressource (toujours en attente de modération)."""
    from services.auth_service import ensure_role

    ensure_role(session.get(User, user_id), ("candidat", "moderateur", "administrateur"))
    try:
        payload = ResourceInput(**data)
    except Exception as exc:  # pydantic.ValidationError
        from pydantic import ValidationError

        if not isinstance(exc, ValidationError):
            raise
        details = [f"{'.'.join(str(p) for p in e.get('loc', ()))}: {e.get('msg')}" for e in exc.errors()]
        raise BusinessValidationError("error_validation", details) from exc

    resource = Resource(
        title=payload.title,
        description=payload.description,
        category=payload.category,
        language=payload.language,
        author_name=payload.author_name,
        source_url=payload.source_url,
        content=payload.content,
        status=RESOURCE_PENDING,
        is_demo=False,
        submitted_by=user_id,
    )
    session.add(resource)
    session.flush()
    repo.add_audit_log(
        session,
        actor_id=user_id,
        action="resource.submitted",
        entity_type="resource",
        entity_id=resource.id,
        detail={"category": payload.category, "language": payload.language},
    )
    return resource


def published_resources(
    session: Session, language: Optional[str] = None, category: Optional[str] = None
) -> list[Resource]:
    rows = repo.list_resources(session, status=RESOURCE_PUBLISHED, language=language, category=category)
    return rows


def my_resources(session: Session, user_id: int) -> list[Resource]:
    return [r for r in repo.list_resources(session, limit=500) if r.submitted_by == user_id]


def get_resource_or_error(session: Session, resource_id: int) -> Resource:
    resource = repo.get_resource(session, resource_id)
    if resource is None:
        raise NotFoundError("error_not_found")
    return resource


def report_resource(session: Session, user_id: int, resource_id: int, reason: str) -> Report:
    """Signale une ressource (un signalement ouvert par utilisateur et par ressource)."""
    get_resource_or_error(session, resource_id)
    try:
        payload = ReportInput(resource_id=resource_id, reason=reason)
    except Exception as exc:
        from pydantic import ValidationError

        if not isinstance(exc, ValidationError):
            raise
        raise BusinessValidationError("error_validation", ["reason: invalide"]) from exc

    existing = [
        row
        for row in repo.list_reports(session, status=REPORT_OPEN, limit=500)
        if row.resource_id == resource_id and row.reporter_id == user_id
    ]
    if existing:
        raise BusinessValidationError("error_validation", ["report: déjà ouvert"])

    report = Report(resource_id=resource_id, reporter_id=user_id, reason=payload.reason, status=REPORT_OPEN)
    session.add(report)
    session.flush()
    repo.add_audit_log(
        session,
        actor_id=user_id,
        action="resource.reported",
        entity_type="resource",
        entity_id=resource_id,
        detail={"report_id": report.id},
    )
    return report


def pending_resources(session: Session, actor: Optional[User]) -> list[Resource]:
    """File de modération — réservée aux modérateurs/administrateurs."""
    from services.auth_service import ensure_role

    ensure_role(actor, STAFF_ROLES)
    return repo.list_resources(session, status=RESOURCE_PENDING)


def moderate_resource(
    session: Session,
    actor: Optional[User],
    resource_id: int,
    status: str,
    note: Optional[str] = None,
) -> Resource:
    """Change le statut d'une résolution — réservé aux modérateurs/administrateurs."""
    from services.auth_service import ensure_role

    ensure_role(actor, STAFF_ROLES)
    try:
        payload = ResourceStatusInput(status=status, note=note)
    except ValidationError as exc:
        raise BusinessValidationError(
            "error_validation", [f"{e.get('loc')}: {e.get('msg')}" for e in exc.errors()]
        ) from exc
    if payload.status not in RESOURCE_STATUS_VALUES:
        raise BusinessValidationError("error_validation", ["status: invalide"])

    resource = get_resource_or_error(session, resource_id)
    resource.status = payload.status
    resource.review_note = payload.note
    resource.reviewed_by = actor.id if actor else None
    resource.updated_at = utcnow()
    session.flush()
    repo.add_audit_log(
        session,
        actor_id=actor.id if actor else None,
        action="resource.moderated",
        entity_type="resource",
        entity_id=resource.id,
        detail={"status": payload.status},
    )
    return resource


def list_reports(
    session: Session, actor: Optional[User], status: Optional[str] = None
) -> list[Report]:
    """Liste des signalements — réservée aux modérateurs/administrateurs."""
    from services.auth_service import ensure_role

    ensure_role(actor, STAFF_ROLES)
    return repo.list_reports(session, status=status)


def resolve_report(
    session: Session,
    actor: Optional[User],
    report_id: int,
    status: str = REPORT_RESOLVED,
    note: Optional[str] = None,
) -> Report:
    """Clôt un signalement — réservé aux modérateurs/administrateurs."""
    from services.auth_service import ensure_role

    ensure_role(actor, STAFF_ROLES)
    if status not in (REPORT_RESOLVED, REPORT_DISMISSED):
        raise BusinessValidationError("error_validation", ["status: invalide"])

    report = session.get(Report, report_id)
    if report is None:
        raise NotFoundError("error_not_found")
    report.status = status
    report.resolution_note = note
    report.resolved_by = actor.id if actor else None
    report.resolved_at = utcnow()
    session.flush()
    repo.add_audit_log(
        session,
        actor_id=actor.id if actor else None,
        action="report.resolved",
        entity_type="report",
        entity_id=report.id,
        detail={"status": status},
    )
    return report


def resource_status_counts(session: Session) -> dict[str, int]:
    counts = {status: 0 for status in RESOURCE_STATUS_VALUES}
    for row in repo.list_resources(session, limit=1000):
        counts[row.status] = counts.get(row.status, 0) + 1
    return counts


__all__ = [
    "RESOURCE_STATUS_VALUES",
    "STAFF_ROLES",
    "list_reports",
    "moderate_resource",
    "my_resources",
    "pending_resources",
    "published_resources",
    "report_resource",
    "resolve_report",
    "resource_status_counts",
    "submit_resource",
]
