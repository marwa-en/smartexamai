"""SmartExamAI — Service Étudiant : consultation des notes et relevé de notes."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from core.exceptions import UserNotFoundError
from modelss.enums import RoleUtilisateur
from modelss.resultat import Resultat
from modelss.user import User
from repositories.exam_repository import ExamenRepository
from repositories.resultat_repository import ResultatRepository
from repositories.user_repository import UserRepository
from configss.settings import settings


class EtudiantService:
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
        self.resultat_repo = ResultatRepository(db)
        self.examen_repo = ExamenRepository(db)

    def consulter_notes(self, etudiant_id: int) -> List[Dict[str, Any]]:
        """Retourne, pour chaque résultat validé, un résumé lisible
        (titre de l'examen, matière, note finale)."""
        etudiant = self._get_etudiant_or_raise(etudiant_id)
        resultats = self.resultat_repo.list_by_etudiant(etudiant_id)

        notes: List[Dict[str, Any]] = []
        for resultat in resultats:
            if resultat.statut != "succes":
                continue
            examen = self.examen_repo.get(resultat.examen_id)
            notes.append(
                {
                    "examen": examen.titre if examen else None,
                    "matiere": examen.matiere.nom if examen and examen.matiere else None,
                    "date_examen": examen.date_examen.isoformat() if examen and examen.date_examen else None,
                    "note": resultat.note_finale,
                    "note_max": resultat.max_score,
                    "pourcentage": resultat.percentage,
                    "valide_par_professeur": resultat.valide_par_professeur,
                    "commentaire": resultat.commentaire_professeur,
                }
            )
        return notes

    def telecharger_releve(self, etudiant_id: int) -> Path:
        """Génère un relevé de notes (PDF si `reportlab` est disponible,
        sinon fichier texte formaté) et retourne son chemin absolu.

        Ce fichier est un artefact standalone : à connecter plus tard à
        une interface web pour un vrai téléchargement HTTP.
        """
        etudiant = self._get_etudiant_or_raise(etudiant_id)
        notes = self.consulter_notes(etudiant_id)

        output_dir = settings.storage_root / "releves"
        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            return self._generer_releve_pdf(etudiant, notes, output_dir)
        except ImportError:
            return self._generer_releve_texte(etudiant, notes, output_dir)

    # ------------------------------------------------------------------
    # Génération du fichier
    # ------------------------------------------------------------------

    def _generer_releve_pdf(self, etudiant: User, notes: List[Dict[str, Any]], output_dir: Path) -> Path:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas

        path = output_dir / f"releve_{etudiant.id}.pdf"
        c = canvas.Canvas(str(path), pagesize=A4)
        width, height = A4

        y = height - 60
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, y, "Relevé de notes — SmartExamAI")
        y -= 30
        c.setFont("Helvetica", 11)
        c.drawString(50, y, f"Étudiant : {etudiant.nom_complet}  (CNE : {etudiant.cne or 'N/A'})")
        y -= 15
        c.drawString(50, y, f"Généré le : {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M UTC')}")
        y -= 30

        c.setFont("Helvetica-Bold", 11)
        c.drawString(50, y, "Examen")
        c.drawString(250, y, "Matière")
        c.drawString(380, y, "Note")
        c.drawString(450, y, "Validée")
        y -= 15
        c.line(50, y, 545, y)
        y -= 15

        c.setFont("Helvetica", 10)
        for note in notes:
            if y < 60:
                c.showPage()
                y = height - 60
            c.drawString(50, y, str(note["examen"])[:35])
            c.drawString(250, y, str(note["matiere"])[:20])
            note_str = f"{note['note']}/{note['note_max']}" if note["note"] is not None else "N/A"
            c.drawString(380, y, note_str)
            c.drawString(450, y, "Oui" if note["valide_par_professeur"] else "Non")
            y -= 18

        c.save()
        return path

    def _generer_releve_texte(self, etudiant: User, notes: List[Dict[str, Any]], output_dir: Path) -> Path:
        path = output_dir / f"releve_{etudiant.id}.txt"
        lines = [
            "=" * 60,
            "RELEVÉ DE NOTES — SmartExamAI",
            "=" * 60,
            f"Étudiant : {etudiant.nom_complet}  (CNE : {etudiant.cne or 'N/A'})",
            f"Généré le : {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M UTC')}",
            "-" * 60,
        ]
        for note in notes:
            note_str = f"{note['note']}/{note['note_max']}" if note["note"] is not None else "N/A"
            lines.append(
                f"{note['examen']:<35} | {note['matiere']:<15} | {note_str:<8} | "
                f"{'Validée' if note['valide_par_professeur'] else 'En attente'}"
            )
        path.write_text("\n".join(lines), encoding="utf-8")
        return path

    def _get_etudiant_or_raise(self, etudiant_id: int) -> User:
        etudiant = self.user_repo.get(etudiant_id)
        if etudiant is None or etudiant.role != RoleUtilisateur.ETUDIANT.value:
            raise UserNotFoundError(f"Étudiant id={etudiant_id} introuvable.")
        return etudiant
