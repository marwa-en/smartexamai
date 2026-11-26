"""SmartExamAI — Service Administrateur : gestion des comptes utilisateurs."""
from __future__ import annotations

from typing import List, Optional

from sqlalchemy.orm import Session

from core.exceptions import DuplicateEntityError, UserNotFoundError
from core.security import hash_password
from modelss.enums import RoleUtilisateur
from modelss.user import User
from repositories.user_repository import UserRepository


class UserManagementService:
    """Opérations réservées à l'administrateur sur les comptes utilisateurs."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = UserRepository(db)

    def create_user(
        self,
        *,
        username: str,
        email: str,
        password: str,
        role: RoleUtilisateur,
        nom: str,
        prenom: str,
        cne: Optional[str] = None,
        classe_id: Optional[int] = None,
    ) -> User:
        if self.repo.get_by_username(username) is not None:
            raise DuplicateEntityError(f"Le nom d'utilisateur '{username}' existe déjà.")
        if self.repo.get_by_email(email) is not None:
            raise DuplicateEntityError(f"L'email '{email}' est déjà utilisé.")

        user = User(
            username=username,
            email=email,
            password_hash=hash_password(password),
            role=role.value,
            nom=nom,
            prenom=prenom,
            cne=cne,
            classe_id=classe_id if role == RoleUtilisateur.ETUDIANT else None,
            is_active=True,
        )
        return self.repo.add(user)

    def update_user(self, user_id: int, **fields) -> User:
        user = self._get_or_raise(user_id)
        for key, value in fields.items():
            if key == "password" and value:
                user.password_hash = hash_password(value)
            elif hasattr(user, key) and key not in ("id", "password_hash"):
                setattr(user, key, value)
        self.db.flush()
        return user

    def deactivate_user(self, user_id: int) -> User:
        user = self._get_or_raise(user_id)
        user.is_active = False
        self.db.flush()
        return user

    def reactivate_user(self, user_id: int) -> User:
        user = self._get_or_raise(user_id)
        user.is_active = True
        self.db.flush()
        return user

    def get_user(self, user_id: int) -> User:
        return self._get_or_raise(user_id)

    def list_users(self, role: Optional[RoleUtilisateur] = None) -> List[User]:
        if role is not None:
            return self.repo.list_by_role(role)
        return self.repo.list_all()

    def _get_or_raise(self, user_id: int) -> User:
        user = self.repo.get(user_id)
        if user is None:
            raise UserNotFoundError(f"Utilisateur id={user_id} introuvable.")
        return user
