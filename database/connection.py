"""Connexion et initialisation de la base de données — NextStep Maroc.

Responsabilités :
* créer l'engine SQLAlchemy à partir d'une URL (env. ``NEXTSTEP_DATABASE_URL``) ;
* activer les clés étrangères sur SQLite ;
* fournir un gestionnaire de session de court-cycle (``db_session``) ;
* initialiser le schéma de façon **idempotente** (jamais de ``drop``).

La logique métier ne doit jamais dépendre du moteur : seul ce module connaît
la chaîne de connexion, ce qui autorise une migration ultérieure vers PostgreSQL
en changeant uniquement la variable d'environnement.
"""

from __future__ import annotations

import os
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional

try:  # python-dotenv figure dans requirements.txt (.env n'est jamais commité)
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover - dépendance absente
    pass

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from .models import Base

# Racine du projet (répertoire contenant app.py).
BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = BASE_DIR / "data" / "nextstep.db"

_lock = threading.Lock()
_database: Optional["Database"] = None


def resolve_database_url(url: Optional[str] = None) -> str:
    """Retourne une URL absolue et exploitable.

    * ``None`` -> variable d'environnement puis chemin par défaut ;
    * URL SQLite relative -> résolue par rapport à la racine du projet.
    """
    raw = url or os.environ.get("NEXTSTEP_DATABASE_URL") or f"sqlite:///{DEFAULT_DB_PATH.as_posix()}"
    raw = raw.strip()
    if raw.startswith("sqlite:///") and not raw.startswith("sqlite:///:memory:"):
        path_part = raw[len("sqlite:///"):]
        # sqlite:///C:/... (absolu) ou sqlite:///data/x.db (relatif)
        if not (path_part.startswith("/") or (len(path_part) > 2 and path_part[1] == ":")):
            absolute = (BASE_DIR / path_part).resolve()
            absolute.parent.mkdir(parents=True, exist_ok=True)
            raw = f"sqlite:///{absolute.as_posix()}"
    return raw


def create_db_engine(url: str) -> Engine:
    """Crée un engine avec les réglages adaptés au moteur."""
    is_sqlite = url.startswith("sqlite")
    connect_args = {"check_same_thread": False} if is_sqlite else {}
    engine = create_engine(url, future=True, connect_args=connect_args, pool_pre_ping=True)

    if is_sqlite and url not in ("sqlite://", "sqlite:///:memory:"):
        @event.listens_for(engine, "connect")
        def _enable_foreign_keys(dbapi_connection, _record):  # pragma: no cover - callback SQL
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
    return engine


class Database:
    """Ensemble (engine + sessionmaker) pour une URL donnée."""

    def __init__(self, url: str) -> None:
        self.url = url
        is_memory = url in ("sqlite://", "sqlite:///:memory:")
        if is_memory:
            # Nécessaire pour qu'une base mémoire reste unique entre threads/tests.
            self.engine = create_engine(
                url, future=True, connect_args={"check_same_thread": False}, poolclass=StaticPool
            )
        else:
            self.engine = create_db_engine(url)
        self.session_factory = sessionmaker(bind=self.engine, expire_on_commit=False, future=True)

    @contextmanager
    def session(self) -> Iterator[Session]:
        """Session de court cycle : commit à la fin, rollback sur erreur."""
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def create_schema(self) -> None:
        """Crée les tables manquantes. N'écrase jamais une base existante."""
        Base.metadata.create_all(bind=self.engine)

    def dispose(self) -> None:
        self.engine.dispose()


def init_database(url: Optional[str] = None) -> Database:
    """Initialise (ou récupère) la base globale de l'application. Idempotent."""
    global _database
    resolved = resolve_database_url(url)
    with _lock:
        if _database is not None and _database.url == resolved:
            return _database
        if _database is not None:
            _database.dispose()
        _database = Database(resolved)
        _database.create_schema()
        return _database


def get_database() -> Database:
    """Retourne la base globale, en l'initialisant si nécessaire."""
    if _database is None:
        return init_database()
    return _database


def reset_database() -> None:
    """Ferme la base globale (utilisé par les tests et la CLI)."""
    global _database
    with _lock:
        if _database is not None:
            _database.dispose()
        _database = None


@contextmanager
def db_session() -> Iterator[Session]:
    """Raccourci : ``with db_session() as s: ...`` sur la base globale."""
    with get_database().session() as session:
        yield session


__all__ = [
    "BASE_DIR",
    "DEFAULT_DB_PATH",
    "Database",
    "create_db_engine",
    "db_session",
    "get_database",
    "init_database",
    "reset_database",
    "resolve_database_url",
]
