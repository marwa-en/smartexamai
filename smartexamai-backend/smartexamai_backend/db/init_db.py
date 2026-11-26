"""
SmartExamAI — Initialisation de la base de données.

Crée toutes les tables déclarées (via l'import des modèles) et,
optionnellement, un compte administrateur par défaut si aucun n'existe.
"""
from __future__ import annotations

import logging
import secrets

from .base import Base
from db.session import engine, session_scope

# Import de tous les modèles pour qu'ils soient enregistrés sur Base.metadata
from modelss.user import User  # noqa: F401
from modelss.enums import RoleUtilisateur
from modelss.academic import Classe, Matiere  # noqa: F401
from modelss.exam import Examen, ExamResources  # noqa: F401
from modelss.copie import CopieExamen  # noqa: F401
from modelss.resultat import Resultat  # noqa: F401
from modelss.refresh_token import RefreshToken  # noqa: F401

from core.security import hash_password, verify_password
from configss.settings import settings


logger = logging.getLogger("smartexamai.init_db")

# Mot de passe par défaut non sécurisé (pour détecter les anciennes installations)
INSECURE_DEFAULT_PASSWORD = "ChangeMe123!"


def generate_admin_password() -> str:
    """Génère un mot de passe admin aléatoire fort."""
    return secrets.token_urlsafe(18)


def init_db(create_default_admin: bool = True) -> None:
    """Crée les tables manquantes et, si demandé, un admin par défaut sécurisé."""
    Base.metadata.create_all(bind=engine)

    if not create_default_admin:
        return

    with session_scope() as db:
        admins = (
            db.query(User)
            .filter(User.role == RoleUtilisateur.ADMIN)
            .all()
        )

        # Cas 1 : aucun admin n'existe -> on crée un admin sécurisé
        if not admins:
            admin_email = settings.admin_bootstrap_email
            admin_username = "admin"
            initial_password = generate_admin_password()

            default_admin = User(
                username=admin_username,
                email=admin_email,
                password_hash=hash_password(initial_password),
                role=RoleUtilisateur.ADMIN,
                nom="Administrateur",
                prenom="Principal",
                is_active=True,
                must_change_password=True,  # ✅ Forcer le changement
            )
            db.add(default_admin)

            logger.warning(
                "🔐 Compte administrateur initial créé :\n"
                "   Username : %s\n"
                "   Email    : %s\n"
                "   Mot de passe initial : %s\n"
                "   ⚠️  Ce mot de passe doit être changé immédiatement après la première connexion.",
                admin_username,
                admin_email,
                initial_password,
            )
         
            return

        # Cas 2 : des admins existent déjà
        # On vérifie si l'un d'eux utilise encore le mot de passe par défaut
        for admin in admins:
            try:
                still_default = verify_password(
                    INSECURE_DEFAULT_PASSWORD,
                    admin.password_hash,
                )
            except Exception:
                still_default = False

            if still_default:
                env = settings.environment

                if env in {"production", "prod"}:
                    raise RuntimeError(
                        "🔒 Sécurité : un compte admin utilise encore le mot de passe par défaut "
                        f"(username={admin.username}). Refus de démarrer en production. "
                        "Changez immédiatement ce mot de passe."
                    )

                # En dev/staging : on force le changement au prochain login
                admin.must_change_password = True
                logger.warning(
                    "⚠️  Mot de passe admin par défaut détecté pour username=%s. "
                    "Changement obligatoire activé.",
                    admin.username,
                )


if __name__ == "__main__":
    init_db()
    print("✅ Base de données initialisée.")