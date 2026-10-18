"""Modèles SQLAlchemy — NextStep Maroc.

Toutes les entités du MVP sont définies ici. Le schéma est volontairement
neutre vis-à-vis du moteur (SQLite aujourd'hui, PostgreSQL possible plus tard) :

* pas de type spécifique à SQLite (les types de base sont portables) ;
* pas de logique métier dans les modèles ;
* dates stockées en UTC (DateTime) ou en date civile (Date) selon le besoin.

Les informations non connues ne sont JAMAIS remplacées par des valeurs
inventées : les colonnes sont nullable et le statut ``verification_status``
indique explicitement le niveau de fiabilité (voir ``VERIFICATION_STATUSES``).
"""

from __future__ import annotations

import datetime as dt
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# ---------------------------------------------------------------------------
# Constantes de domaine
# ---------------------------------------------------------------------------

ROLE_CANDIDATE = "candidat"
ROLE_MODERATOR = "moderateur"
ROLE_ADMIN = "administrateur"
ROLES = (ROLE_CANDIDATE, ROLE_MODERATOR, ROLE_ADMIN)

# Statuts de vérification d'une information.
VERIFICATION_OFFICIAL = "official_verified"      # information officielle vérifiée
VERIFICATION_PENDING = "pending_verification"    # en attente de vérification
VERIFICATION_UNKNOWN = "unknown"                 # information inconnue / indisponible
VERIFICATION_COMMUNITY = "community"             # contenu communautaire
VERIFICATION_DEMO = "demo"                       # jeu de démonstration (non officiel)
VERIFICATION_STATUSES = (
    VERIFICATION_OFFICIAL,
    VERIFICATION_PENDING,
    VERIFICATION_UNKNOWN,
    VERIFICATION_COMMUNITY,
    VERIFICATION_DEMO,
)

# Statuts des ressources communautaires.
RESOURCE_DRAFT = "draft"
RESOURCE_PENDING = "pending"
RESOURCE_PUBLISHED = "published"
RESOURCE_REJECTED = "rejected"
RESOURCE_TO_REVISE = "to_revise"
RESOURCE_ARCHIVED = "archived"
RESOURCE_STATUSES = (
    RESOURCE_DRAFT,
    RESOURCE_PENDING,
    RESOURCE_PUBLISHED,
    RESOURCE_REJECTED,
    RESOURCE_TO_REVISE,
    RESOURCE_ARCHIVED,
)

# Statuts des signalements.
REPORT_OPEN = "open"
REPORT_RESOLVED = "resolved"
REPORT_DISMISSED = "dismissed"

# Types de cible d'un favori.
FAV_SCHOOL = "school"
FAV_PROGRAM = "program"

# Types de critère d'admission.
CRITERION_SERIES = "bac_series"
CRITERION_AVERAGE = "min_average"
CRITERION_EXAM = "exam_type"
CRITERION_OTHER = "other"
CRITERION_TYPES = (CRITERION_SERIES, CRITERION_AVERAGE, CRITERION_EXAM, CRITERION_OTHER)

# Types d'échéance.
DEADLINE_APPLICATION = "candidature"
DEADLINE_EXAM = "concours"
DEADLINE_RESULT = "resultat"
DEADLINE_OTHER = "autre"
DEADLINE_TYPES = (DEADLINE_APPLICATION, DEADLINE_EXAM, DEADLINE_RESULT, DEADLINE_OTHER)

# Séries du baccalauréat marocain les plus courantes (liste non exhaustive,
# utilisée comme filtre : toute autre série peut être saisie librement).
BAC_SERIES = (
    "SVT",
    "PC",
    "Mathématiques",
    "Économie et Gestion",
    "Sciences Économiques",
    "Lettres et Sciences Humaines",
    "Langues Étrangères",
    "Techniques Mathématiques",
    "Techniques Physiques",
)


def utcnow() -> dt.datetime:
    """Horodatage UTC naïf (compatible SQLite et PostgreSQL)."""
    return dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)


class Base(DeclarativeBase):
    """Base déclarative commune à tous les modèles."""


# ---------------------------------------------------------------------------
# Utilisateurs et profils
# ---------------------------------------------------------------------------


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ROLE_CANDIDATE, server_default=ROLE_CANDIDATE
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    language: Mapped[str] = mapped_column(String(5), nullable=False, default="fr", server_default="fr")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow, onupdate=utcnow
    )

    profile: Mapped[Optional["CandidateProfile"]] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("role IN ('candidat','moderateur','administrateur')", name="ck_users_role"),
        CheckConstraint("language IN ('fr','ar','en')", name="ck_users_language"),
        Index("ix_users_role", "role"),
    )

    @property
    def is_admin(self) -> bool:
        return self.role == ROLE_ADMIN

    @property
    def is_staff(self) -> bool:
        """Administrateur ou modérateur (accès à l'espace de modération)."""
        return self.role in (ROLE_ADMIN, ROLE_MODERATOR)


class CandidateProfile(Base):
    __tablename__ = "candidate_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )
    display_name: Mapped[Optional[str]] = mapped_column(String(120))
    bac_series: Mapped[Optional[str]] = mapped_column(String(80))
    bac_year: Mapped[Optional[int]] = mapped_column(Integer)
    city: Mapped[Optional[str]] = mapped_column(String(80))
    average: Mapped[Optional[float]] = mapped_column(Float)  # facultative, /20
    favorite_subjects: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    interests: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    desired_fields: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    geographic_preference: Mapped[Optional[str]] = mapped_column(String(80))
    budget_preference: Mapped[Optional[str]] = mapped_column(String(80))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow, onupdate=utcnow
    )

    user: Mapped[User] = relationship(back_populates="profile")

    __table_args__ = (
        CheckConstraint("average IS NULL OR (average >= 0 AND average <= 20)", name="ck_profile_average"),
        CheckConstraint("bac_year IS NULL OR (bac_year >= 1990 AND bac_year <= 2100)", name="ck_profile_year"),
    )


# ---------------------------------------------------------------------------
# Écoles et formations
# ---------------------------------------------------------------------------


class School(Base):
    __tablename__ = "schools"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    short_name: Mapped[Optional[str]] = mapped_column(String(60))
    city: Mapped[Optional[str]] = mapped_column(String(80), index=True)
    school_type: Mapped[Optional[str]] = mapped_column(String(80))  # grande école, université...
    domain: Mapped[Optional[str]] = mapped_column(String(120), index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    official_url: Mapped[Optional[str]] = mapped_column(String(500))
    verification_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default=VERIFICATION_UNKNOWN, server_default=VERIFICATION_UNKNOWN
    )
    last_verified_at: Mapped[Optional[dt.date]] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow, onupdate=utcnow
    )

    programs: Mapped[list["Program"]] = relationship(
        back_populates="school", cascade="all, delete-orphan", lazy="selectin"
    )

    __table_args__ = (
        CheckConstraint(
            "verification_status IN ('official_verified','pending_verification','unknown','community','demo')",
            name="ck_school_verification",
        ),
        Index("ix_schools_city_domain", "city", "domain"),
    )


class Program(Base):
    __tablename__ = "programs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    school_id: Mapped[int] = mapped_column(
        ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    degree_level: Mapped[Optional[str]] = mapped_column(String(60))  # licence, ingénieur, mastère...
    domain: Mapped[Optional[str]] = mapped_column(String(120), index=True)
    duration_years: Mapped[Optional[float]] = mapped_column(Float)
    teaching_language: Mapped[Optional[str]] = mapped_column(String(20))  # fr / ar / en / bilingue
    description: Mapped[Optional[str]] = mapped_column(Text)
    # Frais : null = inconnu, JAMAIS de valeur inventée.
    tuition_fees_mad: Mapped[Optional[float]] = mapped_column(Float)
    tuition_note: Mapped[Optional[str]] = mapped_column(String(255))
    official_url: Mapped[Optional[str]] = mapped_column(String(500))
    verification_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default=VERIFICATION_UNKNOWN, server_default=VERIFICATION_UNKNOWN
    )
    last_verified_at: Mapped[Optional[dt.date]] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow, onupdate=utcnow
    )

    school: Mapped[School] = relationship(back_populates="programs")
    admission_rules: Mapped[list["AdmissionRule"]] = relationship(
        back_populates="program", cascade="all, delete-orphan", lazy="selectin"
    )
    deadlines: Mapped[list["Deadline"]] = relationship(
        back_populates="program", cascade="all, delete-orphan", lazy="selectin"
    )

    __table_args__ = (
        CheckConstraint(
            "verification_status IN ('official_verified','pending_verification','unknown','community','demo')",
            name="ck_program_verification",
        ),
        CheckConstraint("tuition_fees_mad IS NULL OR tuition_fees_mad >= 0", name="ck_program_tuition"),
        Index("ix_programs_domain_degree", "domain", "degree_level"),
    )


class AdmissionRule(Base):
    """Un ensemble de critères d'admission publié pour une formation."""

    __tablename__ = "admission_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    program_id: Mapped[int] = mapped_column(
        ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    label: Mapped[Optional[str]] = mapped_column(String(200))
    source_name: Mapped[Optional[str]] = mapped_column(String(200))
    source_url: Mapped[Optional[str]] = mapped_column(String(500))
    verification_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default=VERIFICATION_UNKNOWN, server_default=VERIFICATION_UNKNOWN
    )
    verified_at: Mapped[Optional[dt.date]] = mapped_column(Date)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow, onupdate=utcnow
    )

    program: Mapped[Program] = relationship(back_populates="admission_rules")
    criteria: Mapped[list["AdmissionCriterion"]] = relationship(
        back_populates="rule", cascade="all, delete-orphan", lazy="selectin"
    )

    __table_args__ = (
        CheckConstraint(
            "verification_status IN ('official_verified','pending_verification','unknown','community','demo')",
            name="ck_rule_verification",
        ),
    )


class AdmissionCriterion(Base):
    __tablename__ = "admission_criteria"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rule_id: Mapped[int] = mapped_column(
        ForeignKey("admission_rules.id", ondelete="CASCADE"), nullable=False, index=True
    )
    criterion_type: Mapped[str] = mapped_column(String(30), nullable=False)
    # value interprétée selon criterion_type :
    #  - bac_series  -> liste de séries acceptées (JSON list)
    #  - min_average -> nombre (moyenne minimale /20)
    #  - exam_type   -> texte libre (ex. « concours écrit »)
    #  - other       -> texte libre
    value: Mapped[object] = mapped_column(JSON, nullable=False)
    operator: Mapped[Optional[str]] = mapped_column(String(20))  # in / gte / eq / text
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    description: Mapped[Optional[str]] = mapped_column(String(400))
    verification_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default=VERIFICATION_UNKNOWN, server_default=VERIFICATION_UNKNOWN
    )
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, nullable=False, default=utcnow)

    rule: Mapped[AdmissionRule] = relationship(back_populates="criteria")

    __table_args__ = (
        CheckConstraint(
            "criterion_type IN ('bac_series','min_average','exam_type','other')",
            name="ck_criterion_type",
        ),
        CheckConstraint(
            "verification_status IN ('official_verified','pending_verification','unknown','community','demo')",
            name="ck_criterion_verification",
        ),
    )


class Deadline(Base):
    __tablename__ = "deadlines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    school_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("schools.id", ondelete="CASCADE"), index=True
    )
    program_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("programs.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    deadline_type: Mapped[str] = mapped_column(
        String(30), nullable=False, default=DEADLINE_OTHER, server_default=DEADLINE_OTHER
    )
    # date null = information inconnue : affichée comme « Information à vérifier ».
    event_date: Mapped[Optional[dt.date]] = mapped_column(Date)
    source_name: Mapped[Optional[str]] = mapped_column(String(200))
    source_url: Mapped[Optional[str]] = mapped_column(String(500))
    verification_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default=VERIFICATION_UNKNOWN, server_default=VERIFICATION_UNKNOWN
    )
    verified_at: Mapped[Optional[dt.date]] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow, onupdate=utcnow
    )

    school: Mapped[Optional[School]] = relationship()
    program: Mapped[Optional[Program]] = relationship(back_populates="deadlines")

    __table_args__ = (
        CheckConstraint(
            "deadline_type IN ('candidature','concours','resultat','autre')",
            name="ck_deadline_type",
        ),
        CheckConstraint(
            "verification_status IN ('official_verified','pending_verification','unknown','community','demo')",
            name="ck_deadline_verification",
        ),
    )


# ---------------------------------------------------------------------------
# QCM et tentatives
# ---------------------------------------------------------------------------


class Quiz(Base):
    __tablename__ = "quizzes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    subject: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    language: Mapped[str] = mapped_column(String(5), nullable=False, default="fr", server_default="fr")
    difficulty: Mapped[Optional[str]] = mapped_column(String(20))  # facile / moyen / difficile
    provenance: Mapped[Optional[str]] = mapped_column(String(255))
    validation_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default=VERIFICATION_DEMO, server_default=VERIFICATION_DEMO
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow, onupdate=utcnow
    )

    questions: Mapped[list["QuizQuestion"]] = relationship(
        back_populates="quiz", cascade="all, delete-orphan", lazy="selectin", order_by="QuizQuestion.position"
    )

    __table_args__ = (
        CheckConstraint("language IN ('fr','ar','en')", name="ck_quiz_language"),
        CheckConstraint("difficulty IS NULL OR difficulty IN ('facile','moyen','difficile')", name="ck_quiz_difficulty"),
        CheckConstraint(
            "validation_status IN ('official_verified','pending_verification','unknown','community','demo')",
            name="ck_quiz_validation",
        ),
        Index("ix_quizzes_subject_language", "subject", "language"),
    )


class QuizQuestion(Base):
    __tablename__ = "quiz_questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    quiz_id: Mapped[int] = mapped_column(
        ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[Optional[str]] = mapped_column(Text)
    difficulty: Mapped[Optional[str]] = mapped_column(String(20))
    language: Mapped[str] = mapped_column(String(5), nullable=False, default="fr", server_default="fr")
    provenance: Mapped[Optional[str]] = mapped_column(String(255))
    validation_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default=VERIFICATION_DEMO, server_default=VERIFICATION_DEMO
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, nullable=False, default=utcnow)

    quiz: Mapped[Quiz] = relationship(back_populates="questions")
    options: Mapped[list["QuizOption"]] = relationship(
        back_populates="question", cascade="all, delete-orphan", lazy="selectin", order_by="QuizOption.position"
    )

    __table_args__ = (
        CheckConstraint("language IN ('fr','ar','en')", name="ck_question_language"),
        CheckConstraint(
            "validation_status IN ('official_verified','pending_verification','unknown','community','demo')",
            name="ck_question_validation",
        ),
        UniqueConstraint("quiz_id", "position", name="uq_question_position"),
    )


class QuizOption(Base):
    __tablename__ = "quiz_options"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    question_id: Mapped[int] = mapped_column(
        ForeignKey("quiz_questions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")

    question: Mapped[QuizQuestion] = relationship(back_populates="options")

    __table_args__ = (UniqueConstraint("question_id", "position", name="uq_option_position"),)


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    quiz_id: Mapped[int] = mapped_column(
        ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Réponses : {"<question_id>": {"option_id": int, "correct": bool}}
    answers: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    started_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime)
    finished_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, nullable=False, default=utcnow)

    __table_args__ = (
        CheckConstraint("total >= 0", name="ck_attempt_total"),
        CheckConstraint("score >= 0", name="ck_attempt_score"),
        Index("ix_attempts_user_quiz", "user_id", "quiz_id"),
    )


# ---------------------------------------------------------------------------
# Orientation, favoris, signalements, audit
# ---------------------------------------------------------------------------


class OrientationResult(Base):
    __tablename__ = "orientation_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    questionnaire: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    # Résultat : {"pathways": [{"key","label","score","reasons":[]}],
    #             "program_matches": [{"program_id","status","reasons":[]}]}
    result: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, nullable=False, default=utcnow)


class Favorite(Base):
    __tablename__ = "favorites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_type: Mapped[str] = mapped_column(String(10), nullable=False)
    school_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("schools.id", ondelete="CASCADE"), index=True
    )
    program_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("programs.id", ondelete="CASCADE"), index=True
    )
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, nullable=False, default=utcnow)

    school: Mapped[Optional[School]] = relationship()
    program: Mapped[Optional[Program]] = relationship()

    __table_args__ = (
        CheckConstraint("target_type IN ('school','program')", name="ck_favorite_target_type"),
        CheckConstraint(
            "(target_type = 'school' AND school_id IS NOT NULL AND program_id IS NULL) OR "
            "(target_type = 'program' AND program_id IS NOT NULL)",
            name="ck_favorite_consistency",
        ),
        # Le service de favoris vérifie l'unicité avant insertion (les NULL
        # ne sont pas équivalents dans les contraintes uniques SQLite).
        Index("ix_favorites_user_target", "user_id", "target_type"),
    )


class Resource(Base):
    __tablename__ = "resources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    category: Mapped[Optional[str]] = mapped_column(String(80), index=True)
    language: Mapped[str] = mapped_column(String(5), nullable=False, default="fr", server_default="fr")
    author_name: Mapped[Optional[str]] = mapped_column(String(120))
    source_url: Mapped[Optional[str]] = mapped_column(String(500))
    content: Mapped[Optional[str]] = mapped_column(Text)  # contenu rédigé (fiches, résumés)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=RESOURCE_PENDING, server_default=RESOURCE_PENDING, index=True
    )
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    submitted_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    reviewed_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    review_note: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow, onupdate=utcnow
    )

    submitter: Mapped[Optional[User]] = relationship(foreign_keys=[submitted_by])

    __table_args__ = (
        CheckConstraint(
            "status IN ('draft','pending','published','rejected','to_revise','archived')",
            name="ck_resource_status",
        ),
        CheckConstraint("language IN ('fr','ar','en')", name="ck_resource_language"),
    )


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    resource_id: Mapped[int] = mapped_column(
        ForeignKey("resources.id", ondelete="CASCADE"), nullable=False, index=True
    )
    reporter_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=REPORT_OPEN, server_default=REPORT_OPEN, index=True
    )
    resolution_note: Mapped[Optional[str]] = mapped_column(Text)
    resolved_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    resolved_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime)

    resource: Mapped[Resource] = relationship()
    reporter: Mapped[Optional[User]] = relationship(foreign_keys=[reporter_id])

    __table_args__ = (
        CheckConstraint("status IN ('open','resolved','dismissed')", name="ck_report_status"),
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    action: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    entity_type: Mapped[Optional[str]] = mapped_column(String(60))
    entity_id: Mapped[Optional[str]] = mapped_column(String(60))
    detail: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, nullable=False, default=utcnow, index=True)

    actor: Mapped[Optional[User]] = relationship()

    __table_args__ = (Index("ix_audit_action_created", "action", "created_at"),)


# Toutes les entités exposées pour les tests et les seeds.
__all__ = [
    "Base",
    "User",
    "CandidateProfile",
    "School",
    "Program",
    "AdmissionRule",
    "AdmissionCriterion",
    "Deadline",
    "Quiz",
    "QuizQuestion",
    "QuizOption",
    "QuizAttempt",
    "OrientationResult",
    "Favorite",
    "Resource",
    "Report",
    "AuditLog",
]
