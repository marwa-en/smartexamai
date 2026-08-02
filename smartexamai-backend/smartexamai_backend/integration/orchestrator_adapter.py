"""
SmartExamAI — Adaptateur d'intégration avec le pipeline IA.

**Ce module est le SEUL endroit du backend qui importe ai_pipeline.orchestrator.**
Il traduit les entités métier (Examen, ExamResources, CopieExamen, Classe)
en `OrchestratorConfig`, exécute `SmartExamOrchestrator.run()`, et convertit
le `FinalResult` (ou une `OrchestratorError`) en un dictionnaire prêt à être
persisté dans le modèle `Resultat`.

orchestrator.py n'est jamais modifié : il est traité comme une boîte noire.
"""
from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Any, Dict

from ai_pipeline.orchestrator import (
    CodeExerciseMetadata,
    OrchestratorConfig,
    OrchestratorError,
    RedactionMetadata,
    Section,
    SmartExamOrchestrator,
)
from configss.settings import settings
from core.exceptions import CorrectionPipelineError, ExamResourcesIncompleteError
from modelss.copie import CopieExamen
from modelss.exam import Examen, ExamResources

_SECTION_MAP = {
    "info": Section.INFO,
    "qcm": Section.QCM,
    "redaction": Section.REDACTION,
    "code": Section.CODE,
}


def _build_orchestrator_config(
    examen: Examen, ressources: ExamResources, copie: CopieExamen
) -> OrchestratorConfig:
    """Construit un OrchestratorConfig à partir des entités métier.

    Ne fait aucune hypothèse : si un chemin obligatoire manque, l'erreur
    est levée ici, avant même d'instancier le pipeline.
    """
    if not ressources.is_complete():
        raise ExamResourcesIncompleteError(
            f"Ressources incomplètes pour l'examen '{examen.titre}' "
            "(consignes / corrigé / tests unitaires / consignes de code manquants)."
        )

    sections = [_SECTION_MAP[s] for s in ressources.sections if s in _SECTION_MAP]

    work_dir = (
        settings.pipeline_work_root
        / f"examen_{examen.id}"
        / f"copie_{copie.id}"
    )

    return OrchestratorConfig(
        images_dir=Path(copie.images_dir),
        consignes_path=Path(ressources.consignes_path),
        corrige_path=Path(ressources.corrige_path),
        unit_tests_path=Path(ressources.unit_tests_path),
        code_consignes_path=Path(ressources.code_consignes_path)
        if ressources.code_consignes_path
        else None,
        project_root=settings.pipeline_project_root,
        work_dir=work_dir,
        students_csv_path=_students_csv_path(examen),
        qcm_template_path=Path(ressources.qcm_template_path)
        if ressources.qcm_template_path
        else None,
        qcm_answer_key_path=Path(ressources.qcm_answer_key_path)
        if ressources.qcm_answer_key_path
        else None,
        cours_path=Path(ressources.cours_path) if ressources.cours_path else None,
        bareme_path=Path(ressources.bareme_path) if ressources.bareme_path else None,
        sections=sections,
        redaction_metadata=RedactionMetadata(
            matiere=ressources.redaction_matiere or examen.matiere.nom,
            type_examen=ressources.redaction_type_examen or "Examen",
            contexte=ressources.redaction_contexte or "",
        ),
        code_exercise=CodeExerciseMetadata(
            language=ressources.code_language,
            exercise_type=ressources.code_exercise_type,
            title=ressources.code_title,
            function_name=ressources.code_function_name,
            rubric=ressources.code_rubric,
            subject=ressources.code_subject,
            exam_type=ressources.code_exam_type,
        ),
        scoring_system=ressources.scoring_system,
        api_key=settings.api_key,
        openrouter_key=settings.openrouter_key,
        show_progress=False,  # exécution serveur : pas de barre de progression console
        cleanup_work_dir=False,
    )


def _students_csv_path(examen: Examen):
    """Retourne le chemin du CSV des étudiants de la classe de l'examen,
    s'il a été généré (cf. storage.file_storage.write_students_csv)."""
    from storage.file_storage import ressources_dir

    path = ressources_dir(examen.id) / "students.csv"
    return path if path.is_file() else None


def run_correction(examen: Examen, ressources: ExamResources, copie: CopieExamen) -> Dict[str, Any]:
    """Exécute le pipeline de correction pour une copie donnée.

    Retourne un dictionnaire directement compatible avec les champs du
    modèle `Resultat`. Lève `CorrectionPipelineError` en cas d'échec du
    pipeline (erreur remontée par OrchestratorError).
    """
    config = _build_orchestrator_config(examen, ressources, copie)

    try:
        orchestrator = SmartExamOrchestrator(config)
        final = orchestrator.run()
    except OrchestratorError as exc:
        raise CorrectionPipelineError(
            message=str(exc), step=getattr(exc, "step", ""), cause=exc
        ) from exc

    return _final_result_to_resultat_fields(final)


def _final_result_to_resultat_fields(final) -> Dict[str, Any]:
    """Convertit un FinalResult (dataclass) en dict prêt pour `Resultat`."""
    summary = final.summary or {}
    return {
        "statut": "succes",
        "message_erreur": None,
        "student_data": final.student,
        "qcm_result": final.qcm,
        "redaction_result": final.redaction,
        "code_result": final.code,
        "sections_corrected": summary.get("sections_corrected", []),
        "total_score": summary.get("total_score"),
        "max_score": summary.get("max_score"),
        "percentage": summary.get("percentage"),
        "work_dir": final.metadata.get("work_dir"),
        "elapsed_seconds": final.metadata.get("elapsed_seconds"),
    }
