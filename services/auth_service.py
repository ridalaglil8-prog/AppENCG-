"""Service d'authentification, de profil et de permissions — NextStep Maroc.

Sécurité :
* mots de passe hachés avec **bcrypt** (jamais en clair, jamais journalisés) ;
* limitation des tentatives de connexion échouées (``utils.security``) ;
* contrôle de rôle répété au niveau métier via :func:`ensure_role` —
  l'interface ne fait que masquer des boutons, ce n'est **pas** une frontière.

Limitation documentée : ``st.session_state`` et les dictionnaires en mémoire
du rate limiter sont propres à un processus Streamlit. Pour une déployée en
multi-instances, il faut un stockage partagé (Redis/PostgreSQL) ou un service
d'identité externe (OIDC).
"""

from __future__ import annotations

from typing import Any, Iterable, Optional

from pydantic import ValidationError
from sqlalchemy.orm import Session

from database import repositories as repo
from database.models import (
    ROLE_ADMIN,
    ROLE_CANDIDATE,
    ROLE_MODERATOR,
    ROLES,
    CandidateProfile,
    User,
    utcnow,
)
from utils.exceptions import (
    AuthenticationError,
    BusinessValidationError,
    PermissionDenied,
)
from utils.security import (
    hash_password,
    login_rate_limiter,
    password_policy_errors,
    verify_password,
)
from utils.validators import LANGUAGES, LoginInput, ProfileInput, RegistrationInput


def _pydantic_details(error: ValidationError) -> list[str]:
    details: list[str] = []
    for err in error.errors():
        field = ".".join(str(part) for part in err.get("loc", ())) or "?"
        details.append(f"{field}: {err.get('msg', '')}")
    return details


def ensure_role(user: Optional[User], allowed_roles: Iterable[str]) -> User:
    """Contrôle d'autorisation central. Lève :class:`PermissionDenied`."""
    allowed = tuple(allowed_roles)
    if user is None:
        raise PermissionDenied("error_permission", required_roles=allowed)
    if not user.is_active:
        raise PermissionDenied("error_account_disabled", required_roles=allowed)
    if user.role not in allowed:
        raise PermissionDenied("error_permission", required_roles=allowed)
    return user


def ensure_staff(user: Optional[User]) -> User:
    return ensure_role(user, (ROLE_ADMIN, "moderateur"))


def ensure_admin(user: Optional[User]) -> User:
    return ensure_role(user, (ROLE_ADMIN,))


def register_user(
    session: Session,
    email: str,
    password: str,
    language: str = "fr",
    role: str = ROLE_CANDIDATE,
) -> User:
    """Crée un compte candidat (ou un compte administrateur via la CLI)."""
    try:
        payload = RegistrationInput(email=email, password=password, language=language)
    except ValidationError as exc:
        raise BusinessValidationError("error_validation", _pydantic_details(exc)) from exc

    if role not in ROLES:
        raise BusinessValidationError("error_validation", ["role: inconnu"])

    if repo.get_user_by_email(session, payload.email) is not None:
        raise BusinessValidationError("error_email_exists")

    policy = password_policy_errors(payload.password)
    if policy:
        raise BusinessValidationError("error_validation", policy)

    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=role,
        language=payload.language,
        is_active=True,
    )
    session.add(user)
    session.flush()
    repo.add_audit_log(
        session,
        actor_id=user.id,
        action="user.register",
        entity_type="user",
        entity_id=user.id,
        detail={"role": role, "language": payload.language},
    )
    return user


def authenticate(
    session: Session,
    email: str,
    password: str,
    limiter=None,
) -> User:
    """Vérifie des identifiants. Lève ``AuthenticationError``/``RateLimitedError``."""
    limiter = limiter or login_rate_limiter
    try:
        payload = LoginInput(email=email, password=password)
    except ValidationError as exc:
        raise BusinessValidationError("error_validation", _pydantic_details(exc)) from exc

    limiter.check(payload.email)

    user = repo.get_user_by_email(session, payload.email)
    if user is None or not verify_password(password or "", user.password_hash):
        limiter.record_failure(payload.email)
        # Message identique que l'utilisateur existe ou non (pas d'énumération).
        raise AuthenticationError("error_credentials")

    if not user.is_active:
        limiter.record_failure(payload.email)
        raise AuthenticationError("error_account_disabled")

    limiter.reset(payload.email)
    repo.add_audit_log(
        session,
        actor_id=user.id,
        action="user.login",
        entity_type="user",
        entity_id=user.id,
        detail={"language": user.language},
    )
    return user


def change_password(session: Session, user: User, current_password: str, new_password: str) -> None:
    """Change le mot de passe après vérification de l'ancien."""
    if not verify_password(current_password or "", user.password_hash):
        raise AuthenticationError("error_credentials")
    policy = password_policy_errors(new_password)
    if policy:
        raise BusinessValidationError("error_validation", policy)
    user.password_hash = hash_password(new_password)
    user.updated_at = utcnow()
    session.flush()
    repo.add_audit_log(
        session, actor_id=user.id, action="user.password_changed", entity_type="user", entity_id=user.id
    )


def update_profile(session: Session, user_id: int, data: dict[str, Any]) -> CandidateProfile:
    """Valide puis enregistre le profil candidat."""
    try:
        payload = ProfileInput(**data)
    except ValidationError as exc:
        raise BusinessValidationError("error_validation", _pydantic_details(exc)) from exc

    profile = repo.upsert_profile(session, user_id, payload.model_dump())
    repo.add_audit_log(
        session,
        actor_id=user_id,
        action="profile.update",
        entity_type="profile",
        entity_id=profile.id,
        detail={"fields": sorted(payload.model_dump(exclude_none=True))},
    )
    return profile


def set_language(session: Session, user: User, language: str) -> User:
    if language not in LANGUAGES:
        raise BusinessValidationError("error_validation", ["language: invalide"])
    user.language = language
    user.updated_at = utcnow()
    session.flush()
    return user


def delete_my_data(session: Session, user_id: int) -> None:
    """Droit à l'effacement : profil, favoris, tentatives et résultats supprimés."""
    repo.delete_user_data(session, user_id)
    repo.add_audit_log(
        session,
        actor_id=None,
        action="user.data_deleted",
        entity_type="user",
        entity_id=user_id,
        detail={"note": "suppression demandée par l'utilisateur"},
    )


def list_users(session: Session) -> list[User]:
    return list(repo.list_users(session))


__all__ = [
    "authenticate",
    "change_password",
    "delete_my_data",
    "ensure_admin",
    "ensure_role",
    "ensure_staff",
    "list_users",
    "register_user",
    "set_language",
    "update_profile",
]
