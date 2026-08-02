"""SmartExamAI — Modèle CopieExamen (copie scannée d'un étudiant)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base
from modelss.enums import StatutCopie


class CopieExamen(Base):
    """Une copie correspond au dossier d'images scannées d'un étudiant
    pour un examen donné (= un `images_dir` pour orchestrator.py)."""

    __tablename__ = "copies_examen"

    id: Mapped[int] = mapped_column(primary_key=True)

    examen_id: Mapped[int] = mapped_column(ForeignKey("examens.id"))
    examen: Mapped["Examen"] = relationship(back_populates="copies")

    # Peut être NULL tant que l'étape d'identification (section "info") n'a pas
    # encore rattaché la copie à un étudiant précis.
    etudiant_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    etudiant: Mapped[Optional["User"]] = relationship(foreign_keys=[etudiant_id])

    images_dir: Mapped[str] = mapped_column(String(500))
    statut: Mapped[str] = mapped_column(String(20), default=StatutCopie.DEPOSEE.value)

    deposee_par_admin_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    resultat: Mapped[Optional["Resultat"]] = relationship(
        back_populates="copie", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<CopieExamen examen={self.examen_id} statut={self.statut}>"
