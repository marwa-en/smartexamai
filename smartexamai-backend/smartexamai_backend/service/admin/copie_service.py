"""SmartExamAI — Service Administrateur : dépôt des copies scannées."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Optional

from sqlalchemy.orm import Session

from core.exceptions import CopieNotFoundError, ExamenNotFoundError
from modelss.copie import CopieExamen
from modelss.enums import StatutCopie
from repositories.copie_repository import CopieRepository
from repositories.exam_repository import ExamenRepository
from storage.file_storage import create_copie_folder, save_copie_images


class CopieService:
    """Permet à l'administrateur de déposer les copies scannées des étudiants."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = CopieRepository(db)
        self.examen_repo = ExamenRepository(db)

    def deposer_copie(
        self,
        *,
        examen_id: int,
        image_paths: Iterable[str | Path],
        etudiant_id: Optional[int] = None,
        deposee_par_admin_id: Optional[int] = None,
    ) -> CopieExamen:
        """Enregistre les pages scannées d'une copie d'étudiant pour un examen.

        `image_paths` est la liste des fichiers image (une page = une image)
        d'une seule copie. Si l'étudiant n'est pas encore connu, il sera
        identifié automatiquement par la section "info" du pipeline lors
        de la correction.
        """
        if self.examen_repo.get(examen_id) is None:
            raise ExamenNotFoundError(f"Examen id={examen_id} introuvable.")

        # Dossier temporaire, renommé après flush() une fois l'id connu
        temp_dir = create_copie_folder(examen_id)
        save_copie_images(temp_dir, image_paths)

        copie = CopieExamen(
            examen_id=examen_id,
            etudiant_id=etudiant_id,
            images_dir=str(temp_dir),
            statut=StatutCopie.DEPOSEE.value,
            deposee_par_admin_id=deposee_par_admin_id,
        )
        self.repo.add(copie)
        return copie

    def get_copie(self, copie_id: int) -> CopieExamen:
        return self._get_or_raise(copie_id)

    def list_copies_by_examen(self, examen_id: int) -> List[CopieExamen]:
        return self.repo.list_by_examen(examen_id)

    def _get_or_raise(self, copie_id: int) -> CopieExamen:
        copie = self.repo.get(copie_id)
        if copie is None:
            raise CopieNotFoundError(f"Copie id={copie_id} introuvable.")
        return copie
