"""SmartExamAI — Modèle utilisateur (rôle unique : admin, professeur, étudiant)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import DateTime, ForeignKey, String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base
from modelss.enums import RoleUtilisateur


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(200))
    role: Mapped[RoleUtilisateur] = mapped_column(String(20))

    nom: Mapped[str] = mapped_column(String(100))
    prenom: Mapped[str] = mapped_column(String(100))
    cne: Mapped[Optional[str]] = mapped_column(String(30), nullable=True, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Uniquement pertinent pour les étudiants
    classe_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("classes.id"), nullable=True
    )
    classe: Mapped[Optional["Classe"]] = relationship(
        back_populates="etudiants", foreign_keys=[classe_id]
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    # Examens créés en tant que professeur assigné
    examens_assignes: Mapped[List["Examen"]] = relationship(
        back_populates="professeur", foreign_keys="Examen.professeur_id"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<User {self.username} ({self.role})>"

    @property
    def nom_complet(self) -> str:
        return f"{self.prenom} {self.nom}"
