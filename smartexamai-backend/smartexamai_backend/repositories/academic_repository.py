"""SmartExamAI — Repositories pour Classe et Matiere."""
from __future__ import annotations

from typing import Optional

from sqlalchemy import select

from modelss.academic import Classe, Matiere
from repositories.base_repository import BaseRepository


class ClasseRepository(BaseRepository[Classe]):
    model = Classe

    def get_by_nom(self, nom: str) -> Optional[Classe]:
        stmt = select(Classe).where(Classe.nom == nom)
        return self.db.execute(stmt).scalar_one_or_none()


class MatiereRepository(BaseRepository[Matiere]):
    model = Matiere

    def get_by_nom(self, nom: str) -> Optional[Matiere]:
        stmt = select(Matiere).where(Matiere.nom == nom)
        return self.db.execute(stmt).scalar_one_or_none()
