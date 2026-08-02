"""SmartExamAI — Repositories pour Examen et ExamResources."""
from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select

from modelss.exam import Examen, ExamResources
from repositories.base_repository import BaseRepository


class ExamenRepository(BaseRepository[Examen]):
    model = Examen

    def list_by_professeur(self, professeur_id: int) -> List[Examen]:
        stmt = select(Examen).where(Examen.professeur_id == professeur_id)
        return list(self.db.execute(stmt).scalars().all())

    def list_by_classe(self, classe_id: int) -> List[Examen]:
        stmt = select(Examen).where(Examen.classe_id == classe_id)
        return list(self.db.execute(stmt).scalars().all())


class ExamResourcesRepository(BaseRepository[ExamResources]):
    model = ExamResources

    def get_by_examen(self, examen_id: int) -> Optional[ExamResources]:
        stmt = select(ExamResources).where(ExamResources.examen_id == examen_id)
        return self.db.execute(stmt).scalar_one_or_none()
