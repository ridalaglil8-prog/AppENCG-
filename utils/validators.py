"""Validation des données d'entrée (Pydantic) — NextStep Maroc.

Toute donnée saisie par l'utilisateur traverse l'un de ces schémas avant
d'atteindre les services. ``EmailStr`` de Pydantic n'est pas utilisé : il
exige le paquet optionnel ``email-validator`` ; un contrôle d'expression
régulière suffisant est implémenté ici (la validation finale du domaine
reste faite par la contrainte d'unicité en base).
"""

from __future__ import annotations

import re
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator

from database.models import (
    BAC_SERIES,
    CRITERION_TYPES,
    DEADLINE_TYPES,
    RESOURCE_STATUSES,
    ROLES,
    VERIFICATION_STATUSES,
)

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")
NAME_RE = re.compile(r"^[^<>{}]{0,120}$")

LANGUAGES = ("fr", "ar", "en")


def _clean(value: Any) -> Any:
    return value.strip() if isinstance(value, str) else value


class RegistrationInput(BaseModel):
    """Formulaire d'inscription."""

    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=8, max_length=72)
    language: str = "fr"

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not EMAIL_RE.match(value):
            raise ValueError("adresse_email_invalide")
        return value

    @field_validator("language")
    @classmethod
    def validate_language(cls, value: str) -> str:
        if value not in LANGUAGES:
            raise ValueError("langue_invalide")
        return value

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("mot_de_passe_trop_long")
        return value


class LoginInput(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class ProfileInput(BaseModel):
    """Profil candidat — seules les données utiles sont collectées."""

    display_name: Optional[str] = None
    bac_series: Optional[str] = None
    bac_year: Optional[int] = Field(default=None, ge=1990, le=2100)
    city: Optional[str] = None
    average: Optional[float] = Field(default=None, ge=0, le=20)
    favorite_subjects: list[str] = Field(default_factory=list)
    interests: list[str] = Field(default_factory=list)
    desired_fields: list[str] = Field(default_factory=list)
    geographic_preference: Optional[str] = None
    budget_preference: Optional[str] = None

    @field_validator("display_name", "city", "geographic_preference", "budget_preference")
    @classmethod
    def validate_text(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        if not value:
            return None
        if not NAME_RE.match(value):
            raise ValueError("caracteres_invalides")
        return value

    @field_validator("bac_series")
    @classmethod
    def validate_series(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        if not value:
            return None
        if len(value) > 80:
            raise ValueError("serie_trop_longue")
        return value

    @field_validator("favorite_subjects", "interests", "desired_fields")
    @classmethod
    def validate_lists(cls, values: list[str]) -> list[str]:
        cleaned: list[str] = []
        for item in values:
            item = _clean(item)
            if not item or item in cleaned:
                continue
            if len(item) > 80:
                raise ValueError("libelle_trop_long")
            cleaned.append(item)
        if len(cleaned) > 30:
            raise ValueError("trop_d_elements")
        return cleaned

    model_config = {"str_strip_whitespace": True}


class SchoolInput(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    short_name: Optional[str] = Field(default=None, max_length=60)
    city: Optional[str] = Field(default=None, max_length=80)
    school_type: Optional[str] = Field(default=None, max_length=80)
    domain: Optional[str] = Field(default=None, max_length=120)
    description: Optional[str] = Field(default=None, max_length=5000)
    official_url: Optional[str] = Field(default=None, max_length=500)
    verification_status: str = "unknown"

    @field_validator("verification_status")
    @classmethod
    def check_status(cls, value: str) -> str:
        if value not in VERIFICATION_STATUSES:
            raise ValueError("statut_verification_invalide")
        return value

    @field_validator("official_url")
    @classmethod
    def check_url(cls, value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        value = value.strip()
        if not value.lower().startswith(("http://", "https://")):
            raise ValueError("url_invalide")
        return value


class ProgramInput(BaseModel):
    school_id: int
    name: str = Field(min_length=2, max_length=200)
    degree_level: Optional[str] = Field(default=None, max_length=60)
    domain: Optional[str] = Field(default=None, max_length=120)
    duration_years: Optional[float] = Field(default=None, ge=0, le=12)
    teaching_language: Optional[str] = Field(default=None, max_length=20)
    description: Optional[str] = Field(default=None, max_length=5000)
    # Frais volontairement facultatifs : null = « Information à vérifier ».
    tuition_fees_mad: Optional[float] = Field(default=None, ge=0)
    tuition_note: Optional[str] = Field(default=None, max_length=255)
    official_url: Optional[str] = Field(default=None, max_length=500)
    verification_status: str = "unknown"

    @field_validator("verification_status")
    @classmethod
    def check_status(cls, value: str) -> str:
        if value not in VERIFICATION_STATUSES:
            raise ValueError("statut_verification_invalide")
        return value


class CriterionInput(BaseModel):
    criterion_type: str
    value: Any
    operator: Optional[str] = None
    is_required: bool = True
    description: Optional[str] = Field(default=None, max_length=400)
    verification_status: str = "unknown"

    @field_validator("criterion_type")
    @classmethod
    def check_type(cls, value: str) -> str:
        if value not in CRITERION_TYPES:
            raise ValueError("type_critere_invalide")
        return value

    @field_validator("verification_status")
    @classmethod
    def check_status(cls, value: str) -> str:
        if value not in VERIFICATION_STATUSES:
            raise ValueError("statut_verification_invalide")
        return value


class AdmissionRuleInput(BaseModel):
    program_id: int
    label: Optional[str] = Field(default=None, max_length=200)
    source_name: Optional[str] = Field(default=None, max_length=200)
    source_url: Optional[str] = Field(default=None, max_length=500)
    verification_status: str = "unknown"
    notes: Optional[str] = Field(default=None, max_length=4000)
    criteria: list[CriterionInput] = Field(default_factory=list)

    @field_validator("verification_status")
    @classmethod
    def check_status(cls, value: str) -> str:
        if value not in VERIFICATION_STATUSES:
            raise ValueError("statut_verification_invalide")
        return value


class DeadlineInput(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    deadline_type: str = "autre"
    event_date: Optional[str] = None  # ISO AAAA-MM-JJ ou None (inconnue)
    school_id: Optional[int] = None
    program_id: Optional[int] = None
    source_name: Optional[str] = Field(default=None, max_length=200)
    source_url: Optional[str] = Field(default=None, max_length=500)
    verification_status: str = "unknown"

    @field_validator("deadline_type")
    @classmethod
    def check_type(cls, value: str) -> str:
        if value not in DEADLINE_TYPES:
            raise ValueError("type_echeance_invalide")
        return value

    @field_validator("verification_status")
    @classmethod
    def check_status(cls, value: str) -> str:
        if value not in VERIFICATION_STATUSES:
            raise ValueError("statut_verification_invalide")
        return value

    def parsed_date(self):
        """Convertit la date ISO ; ``None`` si absente ou invalide."""
        import datetime as dt

        if not self.event_date:
            return None
        try:
            return dt.date.fromisoformat(self.event_date)
        except ValueError:
            return None


class ResourceInput(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    description: Optional[str] = Field(default=None, max_length=5000)
    category: Optional[str] = Field(default=None, max_length=80)
    language: str = "fr"
    author_name: Optional[str] = Field(default=None, max_length=120)
    source_url: Optional[str] = Field(default=None, max_length=500)
    content: Optional[str] = Field(default=None, max_length=50000)

    @field_validator("language")
    @classmethod
    def check_language(cls, value: str) -> str:
        if value not in LANGUAGES:
            raise ValueError("langue_invalide")
        return value


class ReportInput(BaseModel):
    resource_id: int
    reason: str = Field(min_length=5, max_length=1000)


class QuestionInput(BaseModel):
    statement: str = Field(min_length=5, max_length=4000)
    explanation: Optional[str] = Field(default=None, max_length=4000)
    difficulty: Optional[str] = None
    language: str = "fr"
    provenance: Optional[str] = Field(default=None, max_length=255)
    options: list[str] = Field(min_length=2, max_length=6)
    correct_index: int = Field(ge=0)

    @field_validator("difficulty")
    @classmethod
    def check_difficulty(cls, value: Optional[str]) -> Optional[str]:
        if value in (None, ""):
            return None
        if value not in ("facile", "moyen", "difficile"):
            raise ValueError("difficulte_invalide")
        return value

    @field_validator("options")
    @classmethod
    def check_options(cls, values: list[str]) -> list[str]:
        cleaned = [v.strip() for v in values if v and v.strip()]
        if len(cleaned) < 2:
            raise ValueError("options_insuffisantes")
        return cleaned

    @field_validator("correct_index")
    @classmethod
    def check_index(cls, value: int, info) -> int:
        options = info.data.get("options")
        if options is not None and value >= len(options):
            raise ValueError("reponse_invalide")
        return value


class RoleInput(BaseModel):
    role: str

    @field_validator("role")
    @classmethod
    def check_role(cls, value: str) -> str:
        if value not in ROLES:
            raise ValueError("role_invalide")
        return value


class ResourceStatusInput(BaseModel):
    status: str
    note: Optional[str] = Field(default=None, max_length=2000)

    @field_validator("status")
    @classmethod
    def check_status(cls, value: str) -> str:
        if value not in RESOURCE_STATUSES:
            raise ValueError("statut_ressource_invalide")
        return value


# Aide : liste des séries reconnues (filtre UI + validation souple).
KNOWN_BAC_SERIES = tuple(BAC_SERIES)

__all__ = [
    "AdmissionRuleInput",
    "CriterionInput",
    "DeadlineInput",
    "KNOWN_BAC_SERIES",
    "LANGUAGES",
    "LoginInput",
    "ProfileInput",
    "ProgramInput",
    "QuestionInput",
    "RegistrationInput",
    "ReportInput",
    "ResourceInput",
    "ResourceStatusInput",
    "RoleInput",
    "SchoolInput",
]
