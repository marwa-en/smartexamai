"""
SmartExamAI — Service Professeur.

Couvre : définition du barème / corrigé / consignes / tests unitaires,
consultation des résultats et statistiques, validation ou ajustement
des notes calculées automatiquement par le pipeline.
"""
from __future__ import annotations

import statistics
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from core.exceptions import (
    ExamenNotFoundError,
    PermissionDeniedError,
    ResultatNotFoundError,
)
from modelss.exam import Examen, ExamResources
from modelss.resultat import Resultat
from repositories.exam_repository import ExamenRepository, ExamResourcesRepository
from repositories.resultat_repository import ResultatRepository
from storage.file_storage import save_resource_file


class ProfesseurService:
    def __init__(self, db: Session):
        self.db = db
        self.examen_repo = ExamenRepository(db)
        self.resources_repo = ExamResourcesRepository(db)
        self.resultat_repo = ResultatRepository(db)

    # ------------------------------------------------------------------
    # Définition des ressources pédagogiques de l'examen
    # ------------------------------------------------------------------

    def definir_ressources(
        self,
        *,
        examen_id: int,
        professeur_id: int,
        consignes_file: Optional[str | Path] = None,
        corrige_file: Optional[str | Path] = None,
        unit_tests_file: Optional[str | Path] = None,
        code_consignes_file: Optional[str | Path] = None,
        cours_file: Optional[str | Path] = None,
        bareme_file: Optional[str | Path] = None,
        qcm_template_file: Optional[str | Path] = None,
        qcm_answer_key_file: Optional[str | Path] = None,
        sections: Optional[List[str]] = None,
        scoring_system: Optional[str] = None,
        **exercise_metadata: Any,
    ) -> ExamResources:
        """Fournit ou met à jour les ressources de correction d'un examen.

        `exercise_metadata` accepte tout champ additionnel de ExamResources
        (redaction_matiere, code_language, code_rubric, etc.).
        """
        examen = self._get_examen_or_raise(examen_id)
        self._verifier_professeur_assigne(examen, professeur_id)

        ressources = self.resources_repo.get_by_examen(examen_id)
        if ressources is None:
            ressources = ExamResources(examen_id=examen_id)
            self.resources_repo.add(ressources)

        file_fields = {
            "consignes_path": consignes_file,
            "corrige_path": corrige_file,
            "unit_tests_path": unit_tests_file,
            "code_consignes_path": code_consignes_file,
            "cours_path": cours_file,
            "bareme_path": bareme_file,
            "qcm_template_path": qcm_template_file,
            "qcm_answer_key_path": qcm_answer_key_file,
        }
        for attr, source_file in file_fields.items():
            if source_file is not None:
                stored_path = save_resource_file(
                    examen_id, source_file, target_filename=Path(source_file).name
                )
                setattr(ressources, attr, str(stored_path))

        if sections is not None:
            ressources.sections = sections
        if scoring_system is not None:
            ressources.scoring_system = scoring_system

        for key, value in exercise_metadata.items():
            if hasattr(ressources, key):
                setattr(ressources, key, value)

        self.db.flush()
        return ressources

    # ------------------------------------------------------------------
    # Résultats et statistiques
    # ------------------------------------------------------------------

    def consulter_resultats(self, examen_id: int, professeur_id: int) -> List[Resultat]:
        examen = self._get_examen_or_raise(examen_id)
        self._verifier_professeur_assigne(examen, professeur_id)
        return self.resultat_repo.list_by_examen(examen_id)

    def statistiques_examen(self, examen_id: int, professeur_id: int) -> Dict[str, Any]:
        """Calcule des statistiques simples sur les notes finales d'un examen."""
        resultats = self.consulter_resultats(examen_id, professeur_id)
        notes = [
            r.note_finale
            for r in resultats
            if r.statut == "succes" and r.note_finale is not None
        ]

        if not notes:
            return {
                "nombre_copies_corrigees": 0,
                "moyenne": None,
                "mediane": None,
                "note_min": None,
                "note_max": None,
                "taux_echec_pipeline": self._taux_echec(resultats),
            }

        return {
            "nombre_copies_corrigees": len(notes),
            "moyenne": round(statistics.mean(notes), 2),
            "mediane": round(statistics.median(notes), 2),
            "note_min": round(min(notes), 2),
            "note_max": round(max(notes), 2),
            "taux_echec_pipeline": self._taux_echec(resultats),
        }

    @staticmethod
    def _taux_echec(resultats: List[Resultat]) -> float:
        if not resultats:
            return 0.0
        echecs = sum(1 for r in resultats if r.statut == "echec")
        return round(100 * echecs / len(resultats), 2)

    # ------------------------------------------------------------------
    # Validation / ajustement des notes
    # ------------------------------------------------------------------

    def valider_note(self, resultat_id: int, professeur_id: int, commentaire: Optional[str] = None) -> Resultat:
        resultat = self._get_resultat_or_raise(resultat_id)
        self._verifier_professeur_assigne_via_resultat(resultat, professeur_id)
        resultat.valide_par_professeur = True
        if commentaire is not None:
            resultat.commentaire_professeur = commentaire
        self.db.flush()
        return resultat

    def ajuster_note(
        self,
        resultat_id: int,
        professeur_id: int,
        nouvelle_note: float,
        commentaire: Optional[str] = None,
    ) -> Resultat:
        resultat = self._get_resultat_or_raise(resultat_id)
        self._verifier_professeur_assigne_via_resultat(resultat, professeur_id)
        resultat.note_ajustee = nouvelle_note
        resultat.valide_par_professeur = True
        if commentaire is not None:
            resultat.commentaire_professeur = commentaire
        self.db.flush()
        return resultat

    # ------------------------------------------------------------------
    # Utilitaires internes
    # ------------------------------------------------------------------

    def _get_examen_or_raise(self, examen_id: int) -> Examen:
        examen = self.examen_repo.get(examen_id)
        if examen is None:
            raise ExamenNotFoundError(f"Examen id={examen_id} introuvable.")
        return examen

    def _get_resultat_or_raise(self, resultat_id: int) -> Resultat:
        resultat = self.resultat_repo.get(resultat_id)
        if resultat is None:
            raise ResultatNotFoundError(f"Résultat id={resultat_id} introuvable.")
        return resultat

    @staticmethod
    def _verifier_professeur_assigne(examen: Examen, professeur_id: int) -> None:
        if examen.professeur_id != professeur_id:
            raise PermissionDeniedError(
                "Ce professeur n'est pas assigné à cet examen."
            )

    def _verifier_professeur_assigne_via_resultat(self, resultat: Resultat, professeur_id: int) -> None:
        examen = self._get_examen_or_raise(resultat.examen_id)
        self._verifier_professeur_assigne(examen, professeur_id)
