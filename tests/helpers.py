"""Constantes partagées des tests — NextStep Maroc.

Le hachage bcrypt (12 tours) est calculé **une seule fois** puis réutilisé par
tous les comptes de test : le sel étant intégré au hachage, la vérification
reste correcte tout en gardant la suite de tests rapide.
"""

from __future__ import annotations

import sys
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
ROOT = TESTS_DIR.parent
for path in (str(ROOT), str(TESTS_DIR)):
    if path not in sys.path:
        sys.path.insert(0, path)

from utils.security import hash_password  # noqa: E402

TEST_PASSWORD = "Passw0rd!2026"
PASSWORD_HASH = hash_password(TEST_PASSWORD)

__all__ = ["PASSWORD_HASH", "ROOT", "TESTS_DIR", "TEST_PASSWORD"]
