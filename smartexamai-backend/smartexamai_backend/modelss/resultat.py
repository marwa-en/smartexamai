"""
SmartExamAI — Modèle Resultat.

Représente la persistance du FinalResult produit par
ai_pipeline.orchestrator.SmartExamOrchestrator.run(), enrichi des
actions de validation/ajustement du professeur.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base
from modelss.enums import StatutResultat


class Resultat(Base):
    __tablename__ = "resultats"

    id: Mapped[int] = mapped_column(primary_key=True)

    copie_id: Mapped[int] = mapped_column(ForeignKey("copies_examen.id"), unique=True)
    copie: Mapped["CopieExamen"] = relationship(back_populates="resultat")

    examen_id: Mapped[int] = mapped_column(ForeignKey("examens.id"))
    etudiant_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )

    statut: Mapped[str] = mapped_column(String(20))  # StatutResultat
    message_erreur: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # --- Contenu brut du FinalResult (dataclasses.asdict) ---
    student_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    qcm_result: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    redaction_result: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    code_result: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    sections_corrected: Mapped[List[str]] = mapped_column(JSON, default=list)

    # --- Notes calculées automatiquement par le pipeline (FinalResult.summary) ---
    total_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    percentage: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # --- Validation / ajustement par le professeur ---
    valide_par_professeur: Mapped[bool] = mapped_column(Boolean, default=False)
    note_ajustee: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    commentaire_professeur: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    work_dir: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    elapsed_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    @property
    def note_finale(self) -> Optional[float]:
        """Note définitive : celle ajustée par le professeur prévaut,
        sinon la note calculée automatiquement par le pipeline."""
        if self.note_ajustee is not None:
            return self.note_ajustee
        return self.total_score

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Resultat copie={self.copie_id} statut={self.statut}>"
