"""Exceptions métier — NextStep Maroc.

Ces exceptions portent des messages destinés à l'utilisateur final : elles ne
doivent jamais contenir de mot de passe, de jeton ou de détail interne.
"""

from __future__ import annotations


class NextStepError(Exception):
    """Base de toutes les erreurs métier contrôlées."""


class PermissionDenied(NextStepError):
    """L'utilisateur connecté n'a pas le rôle requis pour l'opération."""

    def __init__(self, message: str = "Accès refusé.", required_roles: tuple | list | None = None):
        super().__init__(message)
        self.required_roles = tuple(required_roles or ())


class NotFoundError(NextStepError):
    """Ressource demandée introuvable (identifiant invalide ou désactivé)."""


class BusinessValidationError(NextStepError):
    """Données invalides détectées par la logique métier (au-delà de Pydantic).

    ``message`` est une **clé de traduction** ; ``details`` contient des
    précisions optionnelles (champs en erreur), jamais de secret.
    """

    def __init__(self, message: str = "error_validation", details: list | tuple | None = None):
        super().__init__(message)
        self.details = list(details or [])


class AuthenticationError(NextStepError):
    """Échec d'authentification (identifiants incorrects ou compte désactivé)."""


class RateLimitedError(NextStepError):
    """Trop de tentatives : l'utilisateur doit patienter avant de réessayer."""

    def __init__(self, seconds: int = 0):
        super().__init__("error_rate_limited")
        self.seconds = int(seconds)


__all__ = [
    "NextStepError",
    "PermissionDenied",
    "NotFoundError",
    "BusinessValidationError",
    "AuthenticationError",
    "RateLimitedError",
]
