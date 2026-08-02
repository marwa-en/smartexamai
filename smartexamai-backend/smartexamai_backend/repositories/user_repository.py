"""SmartExamAI — Repository pour l'entité User."""
from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select

from modelss.enums import RoleUtilisateur
from modelss.user import User
from repositories.base_repository import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    def get_by_username(self, username: str) -> Optional[User]:
        stmt = select(User).where(User.username == username)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_email(self, email: str) -> Optional[User]:
        stmt = select(User).where(User.email == email)
        return self.db.execute(stmt).scalar_one_or_none()

    def list_by_role(self, role: RoleUtilisateur) -> List[User]:
        stmt = select(User).where(User.role == role.value)
        return list(self.db.execute(stmt).scalars().all())

    def list_by_classe(self, classe_id: int) -> List[User]:
        stmt = select(User).where(
            User.classe_id == classe_id, User.role == RoleUtilisateur.ETUDIANT.value
        )
        return list(self.db.execute(stmt).scalars().all())
