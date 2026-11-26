"""SmartExamAI — Modèles Classe et Matière."""
from __future__ import annotations

from typing import List, Optional

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


class Classe(Base):
    __tablename__ = "classes"

    id: Mapped[int] = mapped_column(primary_key=True)
    nom: Mapped[str] = mapped_column(String(100), unique=True)
    niveau: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    annee_scolaire: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    etudiants: Mapped[List["User"]] = relationship(
        back_populates="classe", foreign_keys="User.classe_id"
    )
    examens: Mapped[List["Examen"]] = relationship(back_populates="classe")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Classe {self.nom}>"


class Matiere(Base):
    __tablename__ = "matieres"

    id: Mapped[int] = mapped_column(primary_key=True)
    nom: Mapped[str] = mapped_column(String(100), unique=True)
    code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    examens: Mapped[List["Examen"]] = relationship(back_populates="matiere")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Matiere {self.nom}>"
