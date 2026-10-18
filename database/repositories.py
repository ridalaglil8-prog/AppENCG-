"""Accès aux données (repositories) — NextStep Maroc.

Toutes les requêtes passent par l'ORM SQLAlchemy (requêtes paramétrées,
aucune concaténation SQL). Ce module ne contient aucune règle métier et
n'importe jamais Streamlit : il est réutilisable par la CLI, les tests et
l'interface.

Conventions :
* les fonctions prennent une ``Session`` en premier argument ;
* ``add_audit_log`` n'écrit qu'une ligne de journal (jamais de secret).
"""

from __future__ import annotations

import datetime as dt
from typing import Any, Optional, Sequence

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, selectinload

from database.models import (
    FAV_PROGRAM,
    FAV_SCHOOL,
    VERIFICATION_OFFICIAL,
    AdmissionCriterion,
    AdmissionRule,
    AuditLog,
    CandidateProfile,
    Deadline,
    Favorite,
    OrientationResult,
    Program,
    Quiz,
    QuizAttempt,
    Report,
    Resource,
    School,
    User,
)

# --------------------------------------------------------------------------- #
# Utilisateurs et profils
# --------------------------------------------------------------------------- #


def get_user(session: Session, user_id: Optional[int]) -> Optional[User]:
    if not user_id:
        return None
    return session.get(User, user_id)


def get_user_by_email(session: Session, email: str) -> Optional[User]:
    return session.scalar(select(User).where(func.lower(User.email) == (email or "").strip().lower()))


def list_users(session: Session, limit: int = 500) -> Sequence[User]:
    return session.scalars(select(User).order_by(User.created_at.desc()).limit(limit)).all()


def count_users(session: Session) -> int:
    return int(session.scalar(select(func.count(User.id))) or 0)


def get_profile(session: Session, user_id: int) -> Optional[CandidateProfile]:
    return session.scalar(select(CandidateProfile).where(CandidateProfile.user_id == user_id))


def upsert_profile(session: Session, user_id: int, data: dict[str, Any]) -> CandidateProfile:
    """Crée ou met à jour le profil candidat (données validées en amont)."""
    profile = get_profile(session, user_id)
    if profile is None:
        profile = CandidateProfile(user_id=user_id, favorite_subjects=[], interests=[], desired_fields=[])
        session.add(profile)
    for key, value in data.items():
        if hasattr(profile, key):
            setattr(profile, key, value)
    session.flush()
    return profile


def delete_user_data(session: Session, user_id: int) -> None:
    """Supprime les données personnelles d'un utilisateur (droit à l'effacement).

    Les journaux d'audit sont conservés mais anonymisés (``actor_id`` nullable
    avec ``ON DELETE SET NULL``) : la trace d'administration survit, pas la
    personne.
    """
    for model in (Favorite, OrientationResult, QuizAttempt, CandidateProfile):
        session.execute(delete(model).where(model.user_id == user_id))
    user = session.get(User, user_id)
    if user is not None:
        session.delete(user)
    session.flush()


# --------------------------------------------------------------------------- #
# Écoles, formations, critères, échéances
# --------------------------------------------------------------------------- #


def _school_query():
    return select(School).options(selectinload(School.programs).selectinload(Program.admission_rules))


def search_schools(
    session: Session,
    name: Optional[str] = None,
    city: Optional[str] = None,
    domain: Optional[str] = None,
    degree: Optional[str] = None,
    school_type: Optional[str] = None,
    series: Optional[str] = None,
    active_only: bool = True,
    include_demo: bool = True,
) -> list[School]:
    """Recherche/filtre du catalogue.

    ``series`` ne porte que sur les formations dont les séries admissibles sont
    vérifiées (statut ``official_verified``) : le filtrage n'invente donc jamais
    d'admissibilité.
    """
    query = _school_query()
    if active_only:
        query = query.where(School.is_active.is_(True))
    if not include_demo:
        query = query.where(School.verification_status != "demo")

    matched_ids: Optional[set[int]] = None

    if degree:
        prog_ids = session.scalars(
            select(Program.id).where(Program.degree_level == degree, Program.is_active.is_(True))
        ).all()
        matched_ids = set(prog_ids)

    if series:
        crit_ids = session.scalars(
            select(AdmissionCriterion.id).where(
                AdmissionCriterion.criterion_type == "bac_series",
                AdmissionCriterion.verification_status == VERIFICATION_OFFICIAL,
            )
        ).all()
        ok_rules: set[int] = set()
        for crit in session.scalars(
            select(AdmissionCriterion).where(AdmissionCriterion.id.in_(list(crit_ids)))
        ).all():
            values = crit.value if isinstance(crit.value, list) else []
            if series in values:
                ok_rules.add(crit.rule_id)
        prog_ids = session.scalars(
            select(AdmissionRule.program_id).where(AdmissionRule.id.in_(list(ok_rules)))
        ).all() if ok_rules else []
        series_ids = set(prog_ids)
        matched_ids = series_ids if matched_ids is None else (matched_ids & series_ids)

    if matched_ids is not None:
        if not matched_ids:
            return []
        school_ids = session.scalars(
            select(Program.school_id).where(Program.id.in_(matched_ids))
        ).all()
        if not school_ids:
            return []
        query = query.where(School.id.in_(set(school_ids)))

    if name:
        query = query.where(School.name.ilike(f"%{name.strip()}%"))
    if city:
        query = query.where(School.city == city)
    if domain:
        query = query.where(School.domain == domain)
    if school_type:
        query = query.where(School.school_type == school_type)

    schools = session.scalars(query.order_by(School.name)).all()

    # Les filtres portant sur les formations doivent rester cohérents : on ne
    # garde que les écoles dont le programme correspond est déjà présent.
    if degree or series:
        filtered: list[School] = []
        for school in schools:
            keep = []
            for program in school.programs:
                if degree and program.degree_level != degree:
                    continue
                if series:
                    if not any(
                        rule.verification_status == VERIFICATION_OFFICIAL
                        and any(
                            c.criterion_type == "bac_series" and series in (c.value if isinstance(c.value, list) else [])
                            for c in rule.criteria
                        )
                        for rule in program.admission_rules
                    ):
                        continue
                keep.append(program)
            if keep:
                school.programs = keep  # type: ignore[assignment]
                filtered.append(school)
        return filtered
    return list(schools)


def list_cities(session: Session) -> list[str]:
    rows = session.scalars(
        select(School.city).where(School.is_active.is_(True), School.city.is_not(None)).distinct()
    ).all()
    return sorted({r for r in rows if r})


def list_domains(session: Session) -> list[str]:
    rows = session.scalars(
        select(School.domain).where(School.is_active.is_(True), School.domain.is_not(None)).distinct()
    ).all()
    return sorted({r for r in rows if r})


def list_school_types(session: Session) -> list[str]:
    rows = session.scalars(
        select(School.school_type)
        .where(School.is_active.is_(True), School.school_type.is_not(None))
        .distinct()
    ).all()
    return sorted({r for r in rows if r})


def list_degree_levels(session: Session) -> list[str]:
    rows = session.scalars(
        select(Program.degree_level)
        .where(Program.is_active.is_(True), Program.degree_level.is_not(None))
        .distinct()
    ).all()
    return sorted({r for r in rows if r})


def get_school(session: Session, school_id: int) -> Optional[School]:
    return session.scalar(_school_query().where(School.id == school_id))


def get_program(session: Session, program_id: int) -> Optional[Program]:
    return session.scalar(
        select(Program)
        .options(
            selectinload(Program.school),
            selectinload(Program.admission_rules).selectinload(AdmissionRule.criteria),
            selectinload(Program.deadlines),
        )
        .where(Program.id == program_id)
    )


def list_programs_for_school(session: Session, school_id: int) -> list[Program]:
    return list(
        session.scalars(
            select(Program)
            .options(
                selectinload(Program.admission_rules).selectinload(AdmissionRule.criteria),
                selectinload(Program.deadlines),
            )
            .where(Program.school_id == school_id, Program.is_active.is_(True))
            .order_by(Program.name)
        ).all()
    )


def list_all_programs(session: Session, active_only: bool = True) -> list[Program]:
    """Toutes les formations (avec école et critères) — usage orientation/admin."""
    query = select(Program).options(
        selectinload(Program.school),
        selectinload(Program.admission_rules).selectinload(AdmissionRule.criteria),
        selectinload(Program.deadlines),
    )
    if active_only:
        query = query.where(Program.is_active.is_(True))
    return list(session.scalars(query.order_by(Program.name)).all())


def series_with_official_rules(session: Session) -> list[str]:
    """Séries admissibles réellement documentées (statut officiel vérifié)."""
    rows = session.scalars(
        select(AdmissionCriterion.value).where(
            AdmissionCriterion.criterion_type == "bac_series",
            AdmissionCriterion.verification_status == VERIFICATION_OFFICIAL,
        )
    ).all()
    found: set[str] = set()
    for value in rows:
        if isinstance(value, list):
            found.update(v for v in value if isinstance(v, str))
    return sorted(found)


def list_deadlines(
    session: Session,
    confirmed_only: bool = False,
    active_only: bool = True,
    from_date: Optional[dt.date] = None,
    limit: int = 100,
) -> list[Deadline]:
    """Échéances triées : dates renseignées d'abord, puis les dates inconnues.

    ``confirmed_only`` = statut ``official_verified`` + date renseignée.
    """
    query = select(Deadline).options(selectinload(Deadline.school), selectinload(Deadline.program))
    if active_only:
        query = query.where(Deadline.is_active.is_(True))
    if confirmed_only:
        query = query.where(
            Deadline.verification_status == VERIFICATION_OFFICIAL,
            Deadline.event_date.is_not(None),
        )
    if from_date is not None:
        query = query.where(Deadline.event_date.is_not(None), Deadline.event_date >= from_date)
    rows = list(session.scalars(query.limit(limit * 3)).all())
    rows.sort(key=lambda d: (d.event_date is None, d.event_date or dt.date.max, d.title.lower()))
    return rows[:limit]


# --------------------------------------------------------------------------- #
# Favoris
# --------------------------------------------------------------------------- #


def get_favorite(
    session: Session, user_id: int, target_type: str, target_id: int
) -> Optional[Favorite]:
    if target_type == FAV_SCHOOL:
        return session.scalar(
            select(Favorite).where(
                Favorite.user_id == user_id,
                Favorite.target_type == FAV_SCHOOL,
                Favorite.school_id == target_id,
            )
        )
    return session.scalar(
        select(Favorite).where(
            Favorite.user_id == user_id,
            Favorite.target_type == FAV_PROGRAM,
            Favorite.program_id == target_id,
        )
    )


def list_favorites(session: Session, user_id: int) -> list[Favorite]:
    return list(
        session.scalars(
            select(Favorite)
            .options(selectinload(Favorite.school), selectinload(Favorite.program))
            .where(Favorite.user_id == user_id)
            .order_by(Favorite.created_at.desc())
        ).all()
    )


# --------------------------------------------------------------------------- #
# QCM, tentatives, orientation
# --------------------------------------------------------------------------- #


def list_quizzes(session: Session, language: Optional[str] = None, active_only: bool = True) -> list[Quiz]:
    from database.models import QuizQuestion

    query = select(Quiz).options(selectinload(Quiz.questions).selectinload(QuizQuestion.options))
    if active_only:
        query = query.where(Quiz.is_active.is_(True))
    if language:
        query = query.where(Quiz.language == language)
    return list(session.scalars(query.order_by(Quiz.subject, Quiz.title)).all())


def get_quiz(session: Session, quiz_id: int) -> Optional[Quiz]:
    from database.models import QuizQuestion

    return session.scalar(
        select(Quiz)
        .options(selectinload(Quiz.questions).selectinload(QuizQuestion.options))
        .where(Quiz.id == quiz_id)
    )


def list_attempts(
    session: Session, user_id: int, quiz_id: Optional[int] = None, limit: int = 50
) -> list[QuizAttempt]:
    query = select(QuizAttempt).where(QuizAttempt.user_id == user_id)
    if quiz_id:
        query = query.where(QuizAttempt.quiz_id == quiz_id)
    return list(
        session.scalars(query.order_by(QuizAttempt.created_at.desc()).limit(limit)).all()
    )


def progress_by_subject(session: Session, user_id: int) -> list[dict[str, Any]]:
    """Progression agrégée par matière : tentatives, meilleur pourcentage, date."""
    attempts = session.scalars(
        select(QuizAttempt)
        .join(Quiz, Quiz.id == QuizAttempt.quiz_id)
        .where(QuizAttempt.user_id == user_id)
        .order_by(QuizAttempt.created_at)
    ).all()
    buckets: dict[str, dict[str, Any]] = {}
    for attempt in attempts:
        quiz = session.get(Quiz, attempt.quiz_id)
        subject = quiz.subject if quiz else "—"
        pct = round(100.0 * attempt.score / attempt.total, 1) if attempt.total else 0.0
        bucket = buckets.setdefault(
            subject, {"subject": subject, "attempts": 0, "best": 0.0, "last_at": None, "total_questions": 0}
        )
        bucket["attempts"] += 1
        bucket["best"] = max(bucket["best"], pct)
        bucket["last_at"] = attempt.created_at
        if quiz:
            bucket["total_questions"] = len(quiz.questions)
    return sorted(buckets.values(), key=lambda b: b["subject"])


def list_orientation_results(session: Session, user_id: int, limit: int = 5) -> list[OrientationResult]:
    return list(
        session.scalars(
            select(OrientationResult)
            .where(OrientationResult.user_id == user_id)
            .order_by(OrientationResult.created_at.desc())
            .limit(limit)
        ).all()
    )


def latest_orientation_result(session: Session, user_id: int) -> Optional[OrientationResult]:
    results = list_orientation_results(session, user_id, limit=1)
    return results[0] if results else None


# --------------------------------------------------------------------------- #
# Ressources, signalements, audit, statistiques
# --------------------------------------------------------------------------- #


def list_resources(
    session: Session,
    status: Optional[str] = None,
    category: Optional[str] = None,
    language: Optional[str] = None,
    limit: int = 200,
) -> list[Resource]:
    query = select(Resource).options(selectinload(Resource.submitter))
    if status:
        query = query.where(Resource.status == status)
    if category:
        query = query.where(Resource.category == category)
    if language:
        query = query.where(Resource.language == language)
    return list(session.scalars(query.order_by(Resource.created_at.desc()).limit(limit)).all())


def get_resource(session: Session, resource_id: int) -> Optional[Resource]:
    return session.get(Resource, resource_id)


def list_reports(session: Session, status: Optional[str] = None, limit: int = 200) -> list[Report]:
    query = select(Report).options(selectinload(Report.resource), selectinload(Report.reporter))
    if status:
        query = query.where(Report.status == status)
    return list(session.scalars(query.order_by(Report.created_at.desc()).limit(limit)).all())


def add_audit_log(
    session: Session,
    actor_id: Optional[int],
    action: str,
    entity_type: Optional[str] = None,
    entity_id: Optional[Any] = None,
    detail: Optional[dict] = None,
) -> AuditLog:
    """Journalise une opération sensible (aucun secret, aucun mot de passe)."""
    entry = AuditLog(
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        detail=detail or {},
    )
    session.add(entry)
    session.flush()
    return entry


def list_audit_logs(session: Session, limit: int = 200, actor_id: Optional[int] = None) -> list[AuditLog]:
    query = select(AuditLog)
    if actor_id:
        query = query.where(AuditLog.actor_id == actor_id)
    return list(
        session.scalars(query.order_by(AuditLog.created_at.desc()).limit(limit)).all()
    )


def compute_stats(session: Session) -> dict[str, int]:
    """Statistiques réelles calculées à la volée (jamais des valeurs figées)."""
    return {
        "schools": int(session.scalar(select(func.count(School.id)).where(School.is_active.is_(True))) or 0),
        "programs": int(session.scalar(select(func.count(Program.id)).where(Program.is_active.is_(True))) or 0),
        "quizzes": int(session.scalar(select(func.count(Quiz.id)).where(Quiz.is_active.is_(True))) or 0),
        "questions": _count_questions(session),
        "users": count_users(session),
        "resources_published": int(
            session.scalar(select(func.count(Resource.id)).where(Resource.status == "published")) or 0
        ),
        "attempts": int(session.scalar(select(func.count(QuizAttempt.id))) or 0),
        "favorites": int(session.scalar(select(func.count(Favorite.id))) or 0),
        "deadlines_confirmed": int(
            session.scalar(
                select(func.count(Deadline.id)).where(
                    Deadline.verification_status == VERIFICATION_OFFICIAL,
                    Deadline.event_date.is_not(None),
                    Deadline.is_active.is_(True),
                )
            )
            or 0
        ),
    }


def _count_questions(session: Session) -> int:
    from database.models import QuizQuestion

    return int(
        session.scalar(
            select(func.count(QuizQuestion.id))
            .join(Quiz, Quiz.id == QuizQuestion.quiz_id)
            .where(Quiz.is_active.is_(True))
        )
        or 0
    )


__all__ = [
    "add_audit_log",
    "compute_stats",
    "count_users",
    "delete_user_data",
    "get_favorite",
    "get_profile",
    "get_program",
    "get_quiz",
    "get_resource",
    "get_school",
    "get_user",
    "get_user_by_email",
    "latest_orientation_result",
    "list_all_programs",
    "list_attempts",
    "list_audit_logs",
    "list_cities",
    "list_degree_levels",
    "list_deadlines",
    "list_domains",
    "list_favorites",
    "list_orientation_results",
    "list_programs_for_school",
    "list_quizzes",
    "list_reports",
    "list_resources",
    "list_school_types",
    "list_users",
    "progress_by_subject",
    "search_schools",
    "series_with_official_rules",
    "upsert_profile",
]
