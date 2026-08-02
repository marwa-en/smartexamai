"""
SmartExamAI — Initialisation de la base de données.

Crée toutes les tables déclarées (via l'import des modèles) et,
optionnellement, un compte administrateur par défaut si aucun n'existe.
"""
from __future__ import annotations

from .base import Base
from db.session import engine, session_scope

# Import de tous les modèles pour qu'ils soient enregistrés sur Base.metadata
from modelss.user import User  # noqa: F401
from modelss.enums import RoleUtilisateur
from modelss.academic import Classe, Matiere  # noqa: F401
from modelss.exam import Examen, ExamResources  # noqa: F401
from modelss.copie import CopieExamen  # noqa: F401
from modelss.resultat import Resultat  # noqa: F401

from core.security import hash_password


def init_db(create_default_admin: bool = True) -> None:
    """Crée les tables manquantes et, si demandé, un admin par défaut."""
    Base.metadata.create_all(bind=engine)

    if not create_default_admin:
        return

    with session_scope() as db:
        admin_exists = (
            db.query(User).filter(User.role == RoleUtilisateur.ADMIN).first()
        )
        if admin_exists is None:
            default_admin = User(
                username="admin",
                email="admin@smartexamai.local",
                password_hash=hash_password("ChangeMe123!"),
                role=RoleUtilisateur.ADMIN,
                nom="Administrateur",
                prenom="Principal",
                is_active=True,
            )
            db.add(default_admin)
            print(
                "⚙️  Compte administrateur par défaut créé : "
                "username='admin' / mot de passe='ChangeMe123!' "
                "(à changer immédiatement)."
            )


if __name__ == "__main__":
    init_db()
    print("✅ Base de données initialisée.")
