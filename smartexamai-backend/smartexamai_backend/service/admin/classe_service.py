"""SmartExamAI — Service Administrateur : gestion des classes."""
from __future__ import annotations

import csv
import io
from typing import List

from sqlalchemy.orm import Session

from core.exceptions import ClasseNotFoundError, DuplicateEntityError
from modelss.academic import Classe
from modelss.user import User
from repositories.academic_repository import ClasseRepository
from repositories.user_repository import UserRepository
from storage.file_storage import write_students_csv


class ClasseService:
    """Opérations réservées à l'administrateur sur les classes."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = ClasseRepository(db)
        self.user_repo = UserRepository(db)

    def create_classe(self, nom: str, niveau: str | None = None, annee_scolaire: str | None = None) -> Classe:
        if self.repo.get_by_nom(nom) is not None:
            raise DuplicateEntityError(f"La classe '{nom}' existe déjà.")
        classe = Classe(nom=nom, niveau=niveau, annee_scolaire=annee_scolaire)
        return self.repo.add(classe)

    def update_classe(self, classe_id: int, **fields) -> Classe:
        classe = self._get_or_raise(classe_id)
        for key, value in fields.items():
            if hasattr(classe, key) and key != "id":
                setattr(classe, key, value)
        self.db.flush()
        return classe

    def delete_classe(self, classe_id: int) -> None:
        classe = self._get_or_raise(classe_id)
        self.repo.delete(classe)

    def get_classe(self, classe_id: int) -> Classe:
        return self._get_or_raise(classe_id)

    def list_classes(self) -> List[Classe]:
        return self.repo.list_all()

    def list_etudiants(self, classe_id: int) -> List[User]:
        self._get_or_raise(classe_id)
        return self.user_repo.list_by_classe(classe_id)

    def generate_students_csv_for_examen(self, classe_id: int, examen_id: int):
        """Génère le fichier CSV des étudiants d'une classe, dans le format
        attendu par le pipeline pour identifier automatiquement l'étudiant
        (colonnes : nom, prenom, cne, classe).

        Retourne le chemin absolu du fichier généré (students_csv_path).
        """
        classe = self._get_or_raise(classe_id)
        etudiants = self.user_repo.list_by_classe(classe_id)

        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["nom", "prenom", "cne", "classe"])
        for etu in etudiants:
            writer.writerow([etu.nom, etu.prenom, etu.cne or "", classe.nom])

        return write_students_csv(examen_id, buffer.getvalue())

    def _get_or_raise(self, classe_id: int) -> Classe:
        classe = self.repo.get(classe_id)
        if classe is None:
            raise ClasseNotFoundError(f"Classe id={classe_id} introuvable.")
        return classe
