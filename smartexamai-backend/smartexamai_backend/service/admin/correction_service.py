"""
SmartExamAI — Service Administrateur : lancement de la correction automatique.

C'est l'UNIQUE service métier autorisé à déclencher le pipeline IA, via
integration.orchestrator_adapter. Il ne connaît rien du fonctionnement
interne d'orchestrator.py : il transmet les entités et récupère un
résultat déjà normalisé.
"""
from __future__ import annotations
import logging

from typing import List

from sqlalchemy.orm import Session

from core.exceptions import (
    CopieAlreadyProcessingError,
    CopieNotFoundError,
    ExamenNotFoundError,
    ExamResourcesIncompleteError,
    CorrectionPipelineError,
)
from integration.orchestrator_adapter import run_correction
from modelss.copie import CopieExamen
from modelss.enums import StatutCopie, StatutResultat
from modelss.resultat import Resultat
from repositories.copie_repository import CopieRepository
from repositories.exam_repository import ExamenRepository, ExamResourcesRepository
from repositories.resultat_repository import ResultatRepository


class CorrectionService:
    """Orchestration métier du déclenchement de la correction automatique."""

    def __init__(self, db: Session):
        self.db = db
        self.copie_repo = CopieRepository(db)
        self.examen_repo = ExamenRepository(db)
        self.resources_repo = ExamResourcesRepository(db)
        self.resultat_repo = ResultatRepository(db)

    def lancer_correction(self, copie_id: int) -> Resultat:
        """Lance la correction automatique d'une copie précise."""
        copie = self._get_copie_or_raise(copie_id)

        if copie.statut == StatutCopie.EN_CORRECTION.value:
            raise CopieAlreadyProcessingError(
                f"La copie id={copie_id} est déjà '{copie.statut}'."
            )

        examen = self.examen_repo.get(copie.examen_id)
        if examen is None:
            raise ExamenNotFoundError(f"Examen id={copie.examen_id} introuvable.")

        ressources = self.resources_repo.get_by_examen(examen.id)
        if ressources is None or not ressources.is_complete():
            raise ExamResourcesIncompleteError(
                f"Le professeur n'a pas encore fourni toutes les ressources "
                f"nécessaires pour l'examen '{examen.titre}'."
            )

        # Génère automatiquement la liste des étudiants de la classe (CSV)
        # à partir des comptes déjà créés, si la section "info" est activée
        # et qu'aucun fichier n'a été fourni manuellement. Cela évite toute
        # étape manuelle supplémentaire : la liste vient directement de la
        # création des comptes étudiants (User.nom/prenom/cne + classe).
        if "info" in (ressources.sections or []) and not ressources.students_csv_path:
            from service.admin.classe_service import ClasseService

            ressources.students_csv_path = str(
                ClasseService(self.db).generate_students_csv_for_examen(
                    classe_id=examen.classe_id, examen_id=examen.id
                )
            )
            self.db.flush()

        # Une correction précédente (en succès ou en échec) peut déjà exister
        # pour cette copie : on la retire avant d'en réinsérer une nouvelle,
        # afin de permettre de relancer la correction (ex. après avoir
        # complété une ressource manquante) sans violer la contrainte
        # d'unicité sur resultats.copie_id.
        ancien_resultat = self.resultat_repo.get_by_copie(copie_id)
        if ancien_resultat is not None:
            self.resultat_repo.delete(ancien_resultat)

        copie.statut = StatutCopie.EN_CORRECTION.value
        self.db.flush()


        try:
            result_fields = run_correction(examen, ressources, copie)
            copie.statut = StatutCopie.CORRIGEE.value
            
            # ✅ Rattachement automatique de l'étudiant si identifié par le pipeline
                        # ✅ Rattachement automatique de l'étudiant si identifié par le pipeline
            if result_fields.get("student_data"):
                student_data = result_fields["student_data"]
                from modelss.user import User
                from modelss.enums import RoleUtilisateur
                
                matched_student = None
                
                # Le pipeline retourne : {'student_id': 'CNE', 'name': 'Prénom Nom', 'group': 'classe'}
                # Essayer par student_id (qui contient le CNE)
                student_id = student_data.get("student_id")
                if student_id:
                    matched_student = (
                        self.db.query(User)
                        .filter(
                            User.cne == student_id,
                            User.role == RoleUtilisateur.ETUDIANT.value,
                        )
                        .first()
                    )
                
                # Sinon essayer par nom complet
                if not matched_student:
                    name = student_data.get("name")
                    if name:
                        # Parser "Prénom Nom" en deux parties
                        parts = name.strip().split()
                        if len(parts) >= 2:
                            prenom = parts[0]
                            nom = " ".join(parts[1:])
                            matched_student = (
                                self.db.query(User)
                                .filter(
                                    User.nom.ilike(f"%{nom}%"),
                                    User.prenom.ilike(f"%{prenom}%"),
                                    User.role == RoleUtilisateur.ETUDIANT.value,
                                )
                                .first()
                            )
                
                # Rattacher si trouvé
                if matched_student is not None:
                    copie.etudiant_id = matched_student.id
                    result_fields["etudiant_id"] = matched_student.id
                    logging.getLogger(__name__).info(
                        f"Étudiant identifié : {matched_student.username} "
                        f"(CNE: {matched_student.cne})"
                    )
                else:
                    logging.getLogger(__name__).warning(
                        f"Étudiant non trouvé dans la base pour les données : {student_data}"
                    )
            
            resultat = Resultat(
                copie_id=copie.id,
                examen_id=examen.id,
                etudiant_id=result_fields.get("etudiant_id") or copie.etudiant_id,
                **{k: v for k, v in result_fields.items() if k != "etudiant_id"},
            )
        except CorrectionPipelineError as exc:
            copie.statut = StatutCopie.ERREUR.value
            resultat = Resultat(
                copie_id=copie.id,
                examen_id=examen.id,
                etudiant_id=copie.etudiant_id,
                statut=StatutResultat.ECHEC.value,
                message_erreur=str(exc),
                sections_corrected=[],
            )

        self.resultat_repo.add(resultat)
        self.db.flush()
        return resultat

    def lancer_correction_lot(self, examen_id: int) -> List[Resultat]:
        """Lance la correction pour toutes les copies déposées (non encore
        traitées) d'un examen — utile pour un traitement en masse."""
        copies = [
            c
            for c in self.copie_repo.list_by_examen(examen_id)
            if c.statut == StatutCopie.DEPOSEE.value
        ]
        resultats: List[Resultat] = []
        for copie in copies:
            resultats.append(self.lancer_correction(copie.id))
        return resultats

    def _get_copie_or_raise(self, copie_id: int) -> CopieExamen:
        copie = self.copie_repo.get(copie_id)
        if copie is None:
            raise CopieNotFoundError(f"Copie id={copie_id} introuvable.")
        return copie
