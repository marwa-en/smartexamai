"""SmartExamAI — Conversion des entités ORM vers les schémas de sortie de l'API."""
from __future__ import annotations

from typing import Optional

from modelss.academic import Classe
from modelss.copie import CopieExamen
from modelss.exam import Examen, ExamResources
from modelss.resultat import Resultat
from modelss.user import User

from app.schemas import (
    ClasseOut,
    CopieOut,
    ExamenOut,
    ExamResourcesOut,
    ResultatOut,
)


def serialize_classe(classe: Classe) -> ClasseOut:
    return ClasseOut(
        id=classe.id,
        nom=classe.nom,
        niveau=classe.niveau,
        annee_scolaire=classe.annee_scolaire,
        nb_etudiants=len(classe.etudiants or []),
    )


def serialize_resources(res: Optional[ExamResources]) -> Optional[ExamResourcesOut]:
    if res is None:
        return None
    return ExamResourcesOut(
        id=res.id,
        examen_id=res.examen_id,
        consignes_path=res.consignes_path,
        corrige_path=res.corrige_path,
        unit_tests_path=res.unit_tests_path,
        code_consignes_path=res.code_consignes_path,
        cours_path=res.cours_path,
        bareme_path=res.bareme_path,
        qcm_template_path=res.qcm_template_path,
        qcm_answer_key_path=res.qcm_answer_key_path,
        students_csv_path=res.students_csv_path,
        sections=res.sections or [],
        scoring_system=res.scoring_system,
        redaction_matiere=res.redaction_matiere,
        redaction_type_examen=res.redaction_type_examen,
        redaction_contexte=res.redaction_contexte,
        code_language=res.code_language,
        code_exercise_type=res.code_exercise_type,
        code_title=res.code_title,
        code_function_name=res.code_function_name,
        code_rubric=res.code_rubric or {},
        code_subject=res.code_subject,
        code_exam_type=res.code_exam_type,
        is_complete=res.is_complete(),
    )


def serialize_examen(examen: Examen) -> ExamenOut:
    return ExamenOut(
        id=examen.id,
        titre=examen.titre,
        date_examen=examen.date_examen,
        matiere_id=examen.matiere_id,
        classe_id=examen.classe_id,
        professeur_id=examen.professeur_id,
        matiere_nom=examen.matiere.nom if examen.matiere else None,
        classe_nom=examen.classe.nom if examen.classe else None,
        professeur_nom=examen.professeur.nom_complet if examen.professeur else None,
        created_at=examen.created_at,
        ressources=serialize_resources(examen.ressources),
        nb_copies=len(examen.copies or []),
    )


def serialize_copie(copie: CopieExamen) -> CopieOut:
    return CopieOut(
        id=copie.id,
        examen_id=copie.examen_id,
        etudiant_id=copie.etudiant_id,
        etudiant_nom=copie.etudiant.nom_complet if copie.etudiant else None,
        images_dir=copie.images_dir,
        statut=copie.statut,
        created_at=copie.created_at,
    )


def serialize_resultat(resultat: Resultat, etudiant: Optional[User] = None) -> ResultatOut:
    return ResultatOut(
        id=resultat.id,
        copie_id=resultat.copie_id,
        examen_id=resultat.examen_id,
        etudiant_id=resultat.etudiant_id,
        etudiant_nom=etudiant.nom_complet if etudiant else None,
        statut=resultat.statut,
        message_erreur=resultat.message_erreur,
        student_data=resultat.student_data,
        qcm_result=resultat.qcm_result,
        redaction_result=resultat.redaction_result,
        code_result=resultat.code_result,
        sections_corrected=resultat.sections_corrected or [],
        total_score=resultat.total_score,
        max_score=resultat.max_score,
        percentage=resultat.percentage,
        valide_par_professeur=resultat.valide_par_professeur,
        note_ajustee=resultat.note_ajustee,
        note_finale=resultat.note_finale,
        commentaire_professeur=resultat.commentaire_professeur,
        elapsed_seconds=resultat.elapsed_seconds,
        created_at=resultat.created_at,
    )
