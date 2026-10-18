"""Services métier — NextStep Maroc.

Chaque service est une fonction prenant une ``Session`` SQLAlchemy en premier
argument. Aucun service n'importe Streamlit : l'interface ne fait que
transmettre des données déjà validées.
"""

from .auth_service import (  # noqa: F401
    authenticate,
    change_password,
    delete_my_data,
    ensure_role,
    register_user,
    set_language,
    update_profile,
)
