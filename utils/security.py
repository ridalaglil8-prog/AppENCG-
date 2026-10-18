"""Sécurité — hachage des mots de passe et limitation des tentatives.

Choix retenus :
* **bcrypt** (algorithme éprouvé, salage automatique) pour les mots de passe ;
  aucun mot de passe n'est stocké ni journalisé en clair.
* Limitation des tentatives de connexion *par processus* (mémoire), documentée
  comme insuffisante seule pour une mise en production multi-instances :
  en production, il faut un stockage partagé (Redis/PostgreSQL) ou un
  service d'identité managé.

Aucune fonction d'ici ne dépend de Streamlit : elle est testable unitairement.
"""

from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass

import bcrypt

from .exceptions import RateLimitedError

# Politique de mot de passe (borne bcrypt = 72 octets UTF-8).
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 72
BCRYPT_ROUNDS = 12


def hash_password(password: str) -> str:
    """Hache un mot de passe avec bcrypt (salage inclus)."""
    if not isinstance(password, str):
        raise TypeError("Le mot de passe doit être une chaîne.")
    raw = password.encode("utf-8")
    if len(raw) > MAX_PASSWORD_LENGTH:
        raise ValueError(f"Mot de passe trop long (maximum {MAX_PASSWORD_LENGTH} octets).")
    return bcrypt.hashpw(raw, bcrypt.gensalt(rounds=BCRYPT_ROUNDS)).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Vérifie un mot de passe contre son hachage, de façon constante."""
    if not password or not password_hash:
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def password_policy_errors(password: str) -> list[str]:
    """Retourne la liste des violations de la politique (vide si conforme)."""
    errors: list[str] = []
    if not isinstance(password, str) or len(password) < MIN_PASSWORD_LENGTH:
        errors.append(f"password_too_short:{MIN_PASSWORD_LENGTH}")
    elif len(password.encode("utf-8")) > MAX_PASSWORD_LENGTH:
        errors.append(f"password_too_long:{MAX_PASSWORD_LENGTH}")
    return errors


@dataclass
class _AttemptState:
    count: int = 0
    locked_until: float = 0.0


class LoginRateLimiter:
    """Limite les tentatives de connexion échouées par clé (e-mail).

    Paramètres lisibles dans l'environnement :
    * ``NEXTSTEP_MAX_LOGIN_ATTEMPTS`` (défaut : 5) ;
    * ``NEXTSTEP_LOGIN_LOCK_SECONDS`` (défaut : 300).
    """

    def __init__(
        self,
        max_attempts: int | None = None,
        lock_seconds: int | None = None,
        clock=time.monotonic,
    ) -> None:
        self.max_attempts = int(
            max_attempts if max_attempts is not None else os.environ.get("NEXTSTEP_MAX_LOGIN_ATTEMPTS", 5)
        )
        self.lock_seconds = int(
            lock_seconds if lock_seconds is not None else os.environ.get("NEXTSTEP_LOGIN_LOCK_SECONDS", 300)
        )
        self._clock = clock
        self._states: dict[str, _AttemptState] = {}
        self._lock = threading.Lock()

    def check(self, key: str) -> None:
        """Lève :class:`RateLimitedError` si la clé est temporairement bloquée."""
        normalized = key.strip().lower()
        with self._lock:
            state = self._states.get(normalized)
            if state is None:
                return
            if state.locked_until and self._clock() < state.locked_until:
                remaining = int(state.locked_until - self._clock())
                raise RateLimitedError(remaining)
            if state.locked_until and self._clock() >= state.locked_until:
                self._states.pop(normalized, None)

    def record_failure(self, key: str) -> None:
        normalized = key.strip().lower()
        with self._lock:
            state = self._states.setdefault(normalized, _AttemptState())
            state.count += 1
            if state.count >= self.max_attempts:
                state.locked_until = self._clock() + self.lock_seconds

    def reset(self, key: str) -> None:
        """Appelé après une connexion réussie."""
        with self._lock:
            self._states.pop(key.strip().lower(), None)

    def clear(self) -> None:
        with self._lock:
            self._states.clear()


# Instance partagée par le service d'authentification.
login_rate_limiter = LoginRateLimiter()

__all__ = [
    "BCRYPT_ROUNDS",
    "MAX_PASSWORD_LENGTH",
    "MIN_PASSWORD_LENGTH",
    "LoginRateLimiter",
    "hash_password",
    "login_rate_limiter",
    "password_policy_errors",
    "verify_password",
]
