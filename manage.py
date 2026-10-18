"""CLI d'exploitation — NextStep Maroc.

Aucune identifiante n'est codée en dur : l'administrateur est créé à partir des
arguments de la ligne de commande ou des variables d'environnement
(``NEXTSTEP_ADMIN_EMAIL`` / ``NEXTSTEP_ADMIN_PASSWORD``), avec invite
interactive si elles sont absentes.

Commandes :
    python manage.py init-db        # crée le schéma (idempotent, jamais de drop)
    python manage.py create-admin   # crée le premier administrateur
    python manage.py seed-demo      # charge le jeu de données de démonstration
    python manage.py stats          # affiche les compteurs de la base
    python manage.py list-users     # liste les comptes (sans mot de passe)

Exemples :
    python manage.py create-admin --email moi@exemple.ma
    NEXTSTEP_ADMIN_PASSWORD=... python manage.py create-admin --email moi@exemple.ma
"""

from __future__ import annotations

import argparse
import os
import sys

try:  # python-dotenv figure dans requirements.txt
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover - dépendance absente en environnement minimal
    pass

from database import connection  # noqa: E402
from database import repositories as repo  # noqa: E402
from database.seed import load_demo_data  # noqa: E402
from services import auth_service  # noqa: E402
from utils.exceptions import NextStepError  # noqa: E402
from utils.security import password_policy_errors  # noqa: E402

EXAMPLE_EMAIL = "admin@example.com"


def cmd_init_db(_args: argparse.Namespace) -> int:
    database = connection.init_database()
    database.create_schema()
    print(f"Base initialisée : {database.url}")
    print("Schéma créé/mis à jour sans suppression des données existantes.")
    return 0


def _resolve_credentials(args: argparse.Namespace) -> tuple[str, str]:
    email = (args.email or os.environ.get("NEXTSTEP_ADMIN_EMAIL") or "").strip()
    password = args.password or os.environ.get("NEXTSTEP_ADMIN_PASSWORD") or ""

    if not email:
        email = input("E-mail de l'administrateur : ").strip()
    if not password:
        import getpass

        password = getpass.getpass("Mot de passe (8 caractères minimum) : ")
    return email, password


def cmd_create_admin(args: argparse.Namespace) -> int:
    email, password = _resolve_credentials(args)
    if email == EXAMPLE_EMAIL:
        print("Refus : l'adresse d'exemple admin@example.com ne peut pas être utilisée.", file=sys.stderr)
        return 2
    policy = password_policy_errors(password)
    if policy:
        print(f"Mot de passe refusé : {', '.join(policy)}", file=sys.stderr)
        return 2

    connection.init_database()
    try:
        with connection.db_session() as session:
            user = auth_service.register_user(
                session, email, password, language=args.language, role="administrateur"
            )
            print(f"Administrateur créé : {user.email} (id {user.id})")
    except NextStepError as exc:
        print(f"Échec : {exc}", file=sys.stderr)
        return 1
    return 0


def cmd_seed_demo(_args: argparse.Namespace) -> int:
    connection.init_database()
    counts = load_demo_data()
    print("Jeu de démonstration :", counts)
    print("Ces données sont étiquetées « demo » : elles ne sont pas un catalogue officiel.")
    return 0


def cmd_stats(_args: argparse.Namespace) -> int:
    connection.init_database()
    with connection.db_session() as session:
        stats = repo.compute_stats(session)
    width = max((len(key) for key in stats), default=0)
    for key, value in stats.items():
        print(f"{key.ljust(width)} : {value}")
    return 0


def cmd_list_users(_args: argparse.Namespace) -> int:
    connection.init_database()
    with connection.db_session() as session:
        users = repo.list_users(session)
    if not users:
        print("Aucun compte.")
        return 0
    for user in users:
        state = "actif" if user.is_active else "désactivé"
        print(f"{user.email:<40} {user.role:<16} {state:<12} créé le {user.created_at:%Y-%m-%d}")
    print("(les mots de passe ne sont jamais affichés ni journalisés)")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="NextStep Maroc — CLI d'exploitation")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init-db", help="crée le schéma de base (idempotent)")

    admin = sub.add_parser("create-admin", help="crée le premier administrateur")
    admin.add_argument("--email", help="sinon NEXTSTEP_ADMIN_EMAIL")
    admin.add_argument("--password", help="sinon NEXTSTEP_ADMIN_PASSWORD (invite si absent)")
    admin.add_argument("--language", default="fr", choices=["fr", "ar", "en"])

    sub.add_parser("seed-demo", help="charge le jeu de démonstration")
    sub.add_parser("stats", help="affiche les compteurs")
    sub.add_parser("list-users", help="liste les comptes")
    return parser


COMMANDS = {
    "init-db": cmd_init_db,
    "create-admin": cmd_create_admin,
    "seed-demo": cmd_seed_demo,
    "stats": cmd_stats,
    "list-users": cmd_list_users,
}


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return COMMANDS[args.command](args)
    except NextStepError as exc:
        print(f"Erreur métier : {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
