"""
SmartExamAI — Modèles Examen et ExamResources.

ExamResources regroupe exactement les informations que le professeur doit
fournir pour que la correction automatique (ai_pipeline.orchestrator)
puisse s'exécuter : consignes, corrigé, tests unitaires, barème, etc.
Cette séparation permet à l'Admin de créer l'Examen indépendamment du
moment où le Professeur complète ses ressources.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import JSON, Date, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base
from modelss.enums import SystemeNotationQCM


class Examen(Base):
    __tablename__ = "examens"

    id: Mapped[int] = mapped_column(primary_key=True)
    titre: Mapped[str] = mapped_column(String(200))
    date_examen: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    matiere_id: Mapped[int] = mapped_column(ForeignKey("matieres.id"))
    matiere: Mapped["Matiere"] = relationship(back_populates="examens")

    classe_id: Mapped[int] = mapped_column(ForeignKey("classes.id"))
    classe: Mapped["Classe"] = relationship(back_populates="examens")

    professeur_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    professeur: Mapped[Optional["User"]] = relationship(
        back_populates="examens_assignes", foreign_keys=[professeur_id]
    )

    created_by_admin_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    ressources: Mapped[Optional["ExamResources"]] = relationship(
        back_populates="examen", uselist=False, cascade="all, delete-orphan"
    )
    copies: Mapped[List["CopieExamen"]] = relationship(back_populates="examen")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Examen {self.titre}>"


class ExamResources(Base):
    """Ressources pédagogiques fournies par le professeur pour un examen.

    Les champs *_path pointent vers des fichiers gérés par storage/file_storage.py
    (chemins absolus sur disque), directement réutilisables comme arguments
    d'OrchestratorConfig.
    """

    __tablename__ = "exam_resources"

    id: Mapped[int] = mapped_column(primary_key=True)
    examen_id: Mapped[int] = mapped_column(ForeignKey("examens.id"), unique=True)
    examen: Mapped["Examen"] = relationship(back_populates="ressources")

    # --- Fichiers obligatoires pour le pipeline ---
    consignes_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    corrige_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    unit_tests_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    code_consignes_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # --- Fichiers optionnels ---
    cours_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    bareme_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    qcm_template_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    qcm_answer_key_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Fourni par l'ADMINISTRATEUR (et non par le professeur) : liste officielle
    # des étudiants de la classe, utilisée par le pipeline pour identifier
    # automatiquement l'étudiant (section "info"). Peut être généré depuis la
    # Classe (ClasseService.generate_students_csv_for_examen) ou déposé
    # directement par l'admin (ClasseService.import_students_csv_file).
    students_csv_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # --- Paramétrage de la correction ---
    sections: Mapped[List[str]] = mapped_column(
        JSON, default=lambda: ["info", "qcm", "redaction", "code"]
    )
    scoring_system: Mapped[str] = mapped_column(
        String(20), default=SystemeNotationQCM.NORMAL.value
    )

    # --- Métadonnées rédaction (RedactionMetadata côté pipeline) ---
    redaction_matiere: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    redaction_type_examen: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    redaction_contexte: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)

    # --- Métadonnées exercice de code (CodeExerciseMetadata côté pipeline) ---
    code_language: Mapped[str] = mapped_column(String(20), default="python")
    code_exercise_type: Mapped[str] = mapped_column(String(20), default="function")
    code_title: Mapped[str] = mapped_column(String(200), default="Exercice de programmation")
    code_function_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    code_rubric: Mapped[Dict[str, Any]] = mapped_column(JSON, default=lambda: {"total": 20})
    code_subject: Mapped[str] = mapped_column(String(100), default="Informatique")
    code_exam_type: Mapped[str] = mapped_column(String(100), default="Examen")

    def is_complete(self) -> bool:
        """Vérifie que le minimum requis par le pipeline est fourni.

        Reprend les exigences de SmartExamOrchestrator.validate_config() :
        consignes, corrigé et tests unitaires sont toujours nécessaires ;
        code_consignes est requis si la section CODE est activée.
        """
        required = [self.consignes_path, self.corrige_path, self.unit_tests_path]
        if "code" in (self.sections or []):
            required.append(self.code_consignes_path)
        return all(required)