"""SmartExamAI — Service Administrateur : gestion des matières."""
from __future__ import annotations

from typing import List, Optional

from sqlalchemy.orm import Session

from core.exceptions import DuplicateEntityError, MatiereNotFoundError
from modelss.academic import Matiere
from repositories.academic_repository import MatiereRepository


class MatiereService:
    """Opérations réservées à l'administrateur sur les matières."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = MatiereRepository(db)

    def create_matiere(self, nom: str, code: Optional[str] = None) -> Matiere:
        if self.repo.get_by_nom(nom) is not None:
            raise DuplicateEntityError(f"La matière '{nom}' existe déjà.")
        return self.repo.add(Matiere(nom=nom, code=code))

    def update_matiere(self, matiere_id: int, **fields) -> Matiere:
        matiere = self._get_or_raise(matiere_id)
        for key, value in fields.items():
            if hasattr(matiere, key) and key != "id":
                setattr(matiere, key, value)
        self.db.flush()
        return matiere

    def delete_matiere(self, matiere_id: int) -> None:
        matiere = self._get_or_raise(matiere_id)
        self.repo.delete(matiere)

    def get_matiere(self, matiere_id: int) -> Matiere:
        return self._get_or_raise(matiere_id)

    def list_matieres(self) -> List[Matiere]:
        return self.repo.list_all()

    def _get_or_raise(self, matiere_id: int) -> Matiere:
        matiere = self.repo.get(matiere_id)
        if matiere is None:
            raise MatiereNotFoundError(f"Matière id={matiere_id} introuvable.")
        return matiere
