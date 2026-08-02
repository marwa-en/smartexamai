"""SmartExamAI — Service Administrateur : gestion des examens."""
from __future__ import annotations

from datetime import date
from typing import List, Optional

from sqlalchemy.orm import Session

from core.exceptions import ExamenNotFoundError
from modelss.exam import Examen, ExamResources
from repositories.exam_repository import ExamenRepository, ExamResourcesRepository


class ExamenService:
    """Opérations réservées à l'administrateur sur les examens.

    Remarque : la création de l'examen (titre, matière, classe, professeur
    assigné) est distincte de la définition de ses ressources pédagogiques
    (barème, corrigé, consignes...), qui relève du service Professeur
    (cf. services/professeur/professeur_service.py).
    """

    def __init__(self, db: Session):
        self.db = db
        self.repo = ExamenRepository(db)
        self.resources_repo = ExamResourcesRepository(db)

    def create_examen(
        self,
        *,
        titre: str,
        matiere_id: int,
        classe_id: int,
        professeur_id: Optional[int] = None,
        date_examen: Optional[date] = None,
        created_by_admin_id: Optional[int] = None,
    ) -> Examen:
        examen = Examen(
            titre=titre,
            matiere_id=matiere_id,
            classe_id=classe_id,
            professeur_id=professeur_id,
            date_examen=date_examen,
            created_by_admin_id=created_by_admin_id,
        )
        self.repo.add(examen)
        # Une ligne de ressources vide est créée immédiatement : le professeur
        # n'aura qu'à la compléter, jamais à la créer lui-même.
        self.resources_repo.add(ExamResources(examen_id=examen.id))
        self.db.flush()
        return examen

    def assign_professeur(self, examen_id: int, professeur_id: int) -> Examen:
        examen = self._get_or_raise(examen_id)
        examen.professeur_id = professeur_id
        self.db.flush()
        return examen

    def update_examen(self, examen_id: int, **fields) -> Examen:
        examen = self._get_or_raise(examen_id)
        for key, value in fields.items():
            if hasattr(examen, key) and key != "id":
                setattr(examen, key, value)
        self.db.flush()
        return examen

    def delete_examen(self, examen_id: int) -> None:
        examen = self._get_or_raise(examen_id)
        self.repo.delete(examen)

    def get_examen(self, examen_id: int) -> Examen:
        return self._get_or_raise(examen_id)

    def list_examens(self) -> List[Examen]:
        return self.repo.list_all()

    def list_examens_by_classe(self, classe_id: int) -> List[Examen]:
        return self.repo.list_by_classe(classe_id)

    def _get_or_raise(self, examen_id: int) -> Examen:
        examen = self.repo.get(examen_id)
        if examen is None:
            raise ExamenNotFoundError(f"Examen id={examen_id} introuvable.")
        return examen
