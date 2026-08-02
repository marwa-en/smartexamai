"""SmartExamAI — Repository pour CopieExamen."""
from __future__ import annotations

from typing import List

from sqlalchemy import select

from modelss.copie import CopieExamen
from repositories.base_repository import BaseRepository


class CopieRepository(BaseRepository[CopieExamen]):
    model = CopieExamen

    def list_by_examen(self, examen_id: int) -> List[CopieExamen]:
        stmt = select(CopieExamen).where(CopieExamen.examen_id == examen_id)
        return list(self.db.execute(stmt).scalars().all())

    def list_by_etudiant(self, etudiant_id: int) -> List[CopieExamen]:
        stmt = select(CopieExamen).where(CopieExamen.etudiant_id == etudiant_id)
        return list(self.db.execute(stmt).scalars().all())
