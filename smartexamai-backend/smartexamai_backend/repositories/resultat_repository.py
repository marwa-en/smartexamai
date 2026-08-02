"""SmartExamAI — Repository pour Resultat."""
from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select

from modelss.resultat import Resultat
from repositories.base_repository import BaseRepository


class ResultatRepository(BaseRepository[Resultat]):
    model = Resultat

    def get_by_copie(self, copie_id: int) -> Optional[Resultat]:
        stmt = select(Resultat).where(Resultat.copie_id == copie_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def list_by_examen(self, examen_id: int) -> List[Resultat]:
        stmt = select(Resultat).where(Resultat.examen_id == examen_id)
        return list(self.db.execute(stmt).scalars().all())

    def list_by_etudiant(self, etudiant_id: int) -> List[Resultat]:
        stmt = select(Resultat).where(Resultat.etudiant_id == etudiant_id)
        return list(self.db.execute(stmt).scalars().all())
