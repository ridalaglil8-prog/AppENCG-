"""Service d'administration — gestion des données de référence et des comptes.

Toutes les fonctions exigent explicitement un rôle (``administrateur`` ou
``moderateur`` selon l'opération) via :func:`services.auth_service.ensure_role`.
Le contrôle est donc effectué **dans la logique métier**, indépendamment de
l'interface Streamlit.

Étiquetage : seul un **administrateur** peut déclarer une information comme
« Officiel vérifié » (voir :func:`_assert_official_allowed`).
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from database import repositories as repo
from database.models import (
    REPORT_OPEN,
    RESOURCE_PENDING,
    ROLE_ADMIN,
    ROLE_CANDIDATE,
    ROLE_MODERATOR,
    ROLES,
    VERIFICATION_OFFICIAL,
    AdmissionCriterion,
    AdmissionRule,
    AuditLog,
    Deadline,
    Program,
    Quiz,
    QuizOption,
    QuizQuestion,
    Report,
    Resource,
    School,
    User,
    utcnow,
)
from utils.exceptions import BusinessValidationError, NotFoundError, PermissionDenied
from utils.validators import (
    AdmissionRuleInput,
    DeadlineInput,
    ProgramInput,
    QuestionInput,
    ResourceStatusInput,
    RoleInput,
    SchoolInput,
)
from services.auth_service import ensure_admin, ensure_role, ensure_staff

MODERATOR_ROLES = (ROLE_MODERATOR, ROLE_ADMIN)


def _validate(model_cls, data: dict[str, Any]):
    try:
        return model_cls(**data)
    except ValidationError as exc:
        raise BusinessValidationError(
            "error_validation", [f"{'.'.join(str(p) for p in e.get('loc', ()))}: {e.get('msg')}" for e in exc.errors()]
        ) from exc


def _assert_official_allowed(actor: Optional[User], status: str) -> None:
    if status == VERIFICATION_OFFICIAL and (actor is None or actor.role != ROLE_ADMIN):
        raise PermissionDenied("adm_only_official_allowed", required_roles=(ROLE_ADMIN,))


# --------------------------------------------------------------------------- #
# Écoles et formations
# --------------------------------------------------------------------------- #


def create_school(session: Session, actor: User, data: dict[str, Any]) -> School:
    ensure_admin(actor)
    payload = _validate(SchoolInput, data)
    _assert_official_allowed(actor, payload.verification_status)
    school = School(**payload.model_dump())
    session.add(school)
    session.flush()
    repo.add_audit_log(
        session, actor.id, "school.create", "school", school.id, {"name": school.name}
    )
    return school


def update_school(session: Session, actor: User, school_id: int, data: dict[str, Any]) -> School:
    ensure_admin(actor)
    school = session.get(School, school_id)
    if school is None:
        raise NotFoundError("error_not_found")
    payload = _validate(SchoolInput, {**school_as_dict(school), **data})
    _assert_official_allowed(actor, payload.verification_status)
    for key, value in payload.model_dump().items():
        setattr(school, key, value)
    school.updated_at = utcnow()
    session.flush()
    repo.add_audit_log(session, actor.id, "school.update", "school", school.id, {"fields": sorted(data)})
    return school


def set_school_active(session: Session, actor: User, school_id: int, active: bool) -> School:
    ensure_admin(actor)
    school = session.get(School, school_id)
    if school is None:
        raise NotFoundError("error_not_found")
    school.is_active = bool(active)
    school.updated_at = utcnow()
    session.flush()
    repo.add_audit_log(
        session, actor.id, "school.activate" if active else "school.deactivate", "school", school.id, {}
    )
    return school


def school_as_dict(school: School) -> dict[str, Any]:
    return {
        "name": school.name,
        "short_name": school.short_name,
        "city": school.city,
        "school_type": school.school_type,
        "domain": school.domain,
        "description": school.description,
        "official_url": school.official_url,
        "verification_status": school.verification_status,
    }


def create_program(session: Session, actor: User, data: dict[str, Any]) -> Program:
    ensure_admin(actor)
    payload = _validate(ProgramInput, data)
    _assert_official_allowed(actor, payload.verification_status)
    if session.get(School, payload.school_id) is None:
        raise NotFoundError("error_not_found")
    program = Program(**payload.model_dump())
    session.add(program)
    session.flush()
    repo.add_audit_log(
        session, actor.id, "program.create", "program", program.id, {"name": program.name}
    )
    return program


def set_program_active(session: Session, actor: User, program_id: int, active: bool) -> Program:
    ensure_admin(actor)
    program = session.get(Program, program_id)
    if program is None:
        raise NotFoundError("error_not_found")
    program.is_active = bool(active)
    program.updated_at = utcnow()
    session.flush()
    repo.add_audit_log(
        session, actor.id, "program.activate" if active else "program.deactivate", "program", program.id, {}
    )
    return program


# --------------------------------------------------------------------------- #
# Critères d'admission et échéances
# --------------------------------------------------------------------------- #


def add_admission_rule(session: Session, actor: User, data: dict[str, Any]) -> AdmissionRule:
    ensure_admin(actor)
    payload = _validate(AdmissionRuleInput, data)
    _assert_official_allowed(actor, payload.verification_status)
    if session.get(Program, payload.program_id) is None:
        raise NotFoundError("error_not_found")

    rule = AdmissionRule(
        program_id=payload.program_id,
        label=payload.label,
        source_name=payload.source_name,
        source_url=payload.source_url,
        verification_status=payload.verification_status,
        notes=payload.notes,
    )
    session.add(rule)
    session.flush()
    for criterion in payload.criteria:
        session.add(
            AdmissionCriterion(
                rule_id=rule.id,
                criterion_type=criterion.criterion_type,
                value=criterion.value,
                operator=criterion.operator,
                is_required=criterion.is_required,
                description=criterion.description,
                verification_status=criterion.verification_status,
            )
        )
    session.flush()
    repo.add_audit_log(
        session,
        actor.id,
        "rule.create",
        "admission_rule",
        rule.id,
        {"program_id": payload.program_id, "criteria": len(payload.criteria)},
    )
    return rule


def add_deadline(session: Session, actor: User, data: dict[str, Any]) -> Deadline:
    ensure_admin(actor)
    payload = _validate(DeadlineInput, data)
    _assert_official_allowed(actor, payload.verification_status)
    if payload.school_id is None and payload.program_id is None:
        raise BusinessValidationError("error_validation", ["deadline: cible manquante"])
    if payload.program_id is not None and session.get(Program, payload.program_id) is None:
        raise NotFoundError("error_not_found")
    if payload.school_id is not None and session.get(School, payload.school_id) is None:
        raise NotFoundError("error_not_found")

    event_date = payload.parsed_date()
    if payload.event_date and event_date is None:
        raise BusinessValidationError("error_validation", ["event_date: format AAAA-MM-JJ attendu"])
    # Une échéance avec une date ne peut pas être « confirmée » sans source.
    if payload.verification_status == VERIFICATION_OFFICIAL and not payload.source_name:
        raise BusinessValidationError("error_validation", ["source_name: source obligatoire"])

    deadline = Deadline(
        title=payload.title,
        deadline_type=payload.deadline_type,
        event_date=event_date,
        school_id=payload.school_id,
        program_id=payload.program_id,
        source_name=payload.source_name,
        source_url=payload.source_url,
        verification_status=payload.verification_status,
        verified_at=utcnow().date() if payload.verification_status == VERIFICATION_OFFICIAL else None,
    )
    session.add(deadline)
    session.flush()
    repo.add_audit_log(
        session, actor.id, "deadline.create", "deadline", deadline.id, {"title": deadline.title}
    )
    return deadline


# --------------------------------------------------------------------------- #
# QCM
# --------------------------------------------------------------------------- #


def create_quiz(
    session: Session,
    actor: User,
    title: str,
    subject: str,
    language: str = "fr",
    difficulty: Optional[str] = None,
    description: Optional[str] = None,
) -> Quiz:
    ensure_admin(actor)
    if not title.strip() or not subject.strip():
        raise BusinessValidationError("error_validation", ["title: obligatoire", "subject: obligatoire"])
    quiz = Quiz(
        title=title.strip(),
        subject=subject.strip(),
        language=language,
        difficulty=difficulty,
        description=description,
        provenance="Saisi par un administrateur NextStep Maroc",
        validation_status="pending_verification",
    )
    session.add(quiz)
    session.flush()
    repo.add_audit_log(session, actor.id, "quiz.create", "quiz", quiz.id, {"title": quiz.title})
    return quiz


def add_question(session: Session, actor: User, quiz_id: int, data: dict[str, Any]) -> QuizQuestion:
    ensure_admin(actor)
    payload = _validate(QuestionInput, data)
    quiz = session.get(Quiz, quiz_id)
    if quiz is None:
        raise NotFoundError("error_not_found")

    next_position = (
        session.scalar(
            select(func.coalesce(func.max(QuizQuestion.position), 0)).where(QuizQuestion.quiz_id == quiz_id)
        )
        or 0
    ) + 1
    question = QuizQuestion(
        quiz_id=quiz_id,
        statement=payload.statement,
        explanation=payload.explanation,
        difficulty=payload.difficulty,
        language=payload.language,
        provenance=payload.provenance or "Saisi par un administrateur NextStep Maroc",
        validation_status="pending_verification",
        position=next_position,
    )
    session.add(question)
    session.flush()
    for position, text in enumerate(payload.options, start=1):
        session.add(
            QuizOption(
                question_id=question.id,
                text=text,
                is_correct=(position - 1) == payload.correct_index,
                position=position,
            )
        )
    session.flush()
    repo.add_audit_log(
        session, actor.id, "quiz.question_create", "quiz", quiz_id, {"question_id": question.id}
    )
    return question


# --------------------------------------------------------------------------- #
# Comptes et rôles
# --------------------------------------------------------------------------- #


def count_active_admins(session: Session, exclude_user_id: Optional[int] = None) -> int:
    query = select(func.count(User.id)).where(User.role == ROLE_ADMIN, User.is_active.is_(True))
    if exclude_user_id:
        query = query.where(User.id != exclude_user_id)
    return int(session.scalar(query) or 0)


def set_user_role(session: Session, actor: User, user_id: int, role: str) -> User:
    """Change un rôle — réservé aux administrateurs.

    Garde-fous : aucun changement de son propre rôle, et aucun maintien d'un
    compte sans aucun administrateur actif.
    """
    ensure_admin(actor)
    payload = _validate(RoleInput, {"role": role})
    if payload.role not in ROLES:
        raise BusinessValidationError("error_validation", ["role: invalide"])

    target = session.get(User, user_id)
    if target is None:
        raise NotFoundError("error_not_found")
    if target.id == actor.id:
        raise BusinessValidationError("error_validation", ["role: modification de son propre rôle interdite"])
    if target.role == ROLE_ADMIN and payload.role != ROLE_ADMIN and count_active_admins(session, target.id) == 0:
        raise BusinessValidationError("error_validation", ["role: le dernier administrateur actif ne peut être rétrogradé"])

    target.role = payload.role
    target.updated_at = utcnow()
    session.flush()
    repo.add_audit_log(
        session, actor.id, "user.role_change", "user", target.id, {"role": payload.role}
    )
    return target


def set_user_active(session: Session, actor: User, user_id: int, active: bool) -> User:
    ensure_admin(actor)
    target = session.get(User, user_id)
    if target is None:
        raise NotFoundError("error_not_found")
    if target.id == actor.id and not active:
        raise BusinessValidationError("error_validation", ["active: désactivation de son propre compte interdite"])
    if not active and target.role == ROLE_ADMIN and count_active_admins(session, target.id) == 0:
        raise BusinessValidationError("error_validation", ["active: dernier administrateur actif"])

    target.is_active = bool(active)
    target.updated_at = utcnow()
    session.flush()
    repo.add_audit_log(
        session,
        actor.id,
        "user.activate" if active else "user.deactivate",
        "user",
        target.id,
        {"active": bool(active)},
    )
    return target


# --------------------------------------------------------------------------- #
# Consultation (modérateur ou administrateur)
# --------------------------------------------------------------------------- #


def stats(session: Session) -> dict[str, Any]:
    return repo.compute_stats(session)


def staff_stats(session: Session, actor: Optional[User]) -> dict[str, Any]:
    """Statistiques + éléments de modération — réservés au staff."""
    ensure_staff(actor)
    data = repo.compute_stats(session)
    data["users_moderators"] = int(
        session.scalar(select(func.count(User.id)).where(User.role == ROLE_MODERATOR)) or 0
    )
    data["reports_open"] = int(
        session.scalar(select(func.count(Report.id)).where(Report.status == REPORT_OPEN)) or 0
    )
    data["resources_pending"] = int(
        session.scalar(select(func.count(Resource.id)).where(Resource.status == RESOURCE_PENDING)) or 0
    )
    return data


def audit_logs(session: Session, actor: Optional[User], limit: int = 200) -> list[AuditLog]:
    ensure_admin(actor)
    return repo.list_audit_logs(session, limit=limit)


def users_list(session: Session, actor: Optional[User]) -> list[User]:
    ensure_admin(actor)
    return repo.list_users(session)


__all__ = [
    "MODERATOR_ROLES",
    "add_admission_rule",
    "add_deadline",
    "add_question",
    "audit_logs",
    "count_active_admins",
    "create_program",
    "create_quiz",
    "create_school",
    "set_program_active",
    "set_school_active",
    "set_user_active",
    "set_user_role",
    "staff_stats",
    "stats",
    "update_school",
    "users_list",
]
