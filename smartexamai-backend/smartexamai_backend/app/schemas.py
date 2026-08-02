"""SmartExamAI — Schémas Pydantic (requêtes / réponses de l'API FastAPI)."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    role: str
    nom: str
    prenom: str
    cne: Optional[str] = None
    is_active: bool
    classe_id: Optional[int] = None
    nom_complet: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------------------------------------------------------------------------
# Users (admin)
# ---------------------------------------------------------------------------

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: str = Field(pattern="^(admin|professeur|etudiant)$")
    nom: str
    prenom: str
    cne: Optional[str] = None
    classe_id: Optional[int] = None


class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    nom: Optional[str] = None
    prenom: Optional[str] = None
    cne: Optional[str] = None
    classe_id: Optional[int] = None


# ---------------------------------------------------------------------------
# Classes / Matières
# ---------------------------------------------------------------------------

class ClasseCreate(BaseModel):
    nom: str
    niveau: Optional[str] = None
    annee_scolaire: Optional[str] = None


class ClasseUpdate(BaseModel):
    nom: Optional[str] = None
    niveau: Optional[str] = None
    annee_scolaire: Optional[str] = None


class ClasseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nom: str
    niveau: Optional[str] = None
    annee_scolaire: Optional[str] = None
    nb_etudiants: int = 0


class MatiereCreate(BaseModel):
    nom: str
    code: Optional[str] = None


class MatiereUpdate(BaseModel):
    nom: Optional[str] = None
    code: Optional[str] = None


class MatiereOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nom: str
    code: Optional[str] = None


# ---------------------------------------------------------------------------
# Examens
# ---------------------------------------------------------------------------

class ExamenCreate(BaseModel):
    titre: str
    matiere_id: int
    classe_id: int
    professeur_id: Optional[int] = None
    date_examen: Optional[date] = None


class ExamenUpdate(BaseModel):
    titre: Optional[str] = None
    date_examen: Optional[date] = None
    matiere_id: Optional[int] = None
    classe_id: Optional[int] = None


class AssignProfesseurRequest(BaseModel):
    professeur_id: int


class ExamResourcesOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    examen_id: int
    consignes_path: Optional[str] = None
    corrige_path: Optional[str] = None
    unit_tests_path: Optional[str] = None
    code_consignes_path: Optional[str] = None
    cours_path: Optional[str] = None
    bareme_path: Optional[str] = None
    qcm_template_path: Optional[str] = None
    qcm_answer_key_path: Optional[str] = None
    students_csv_path: Optional[str] = None
    sections: List[str] = []
    scoring_system: str
    redaction_matiere: Optional[str] = None
    redaction_type_examen: Optional[str] = None
    redaction_contexte: Optional[str] = None
    code_language: str
    code_exercise_type: str
    code_title: str
    code_function_name: Optional[str] = None
    code_rubric: Dict[str, Any] = {}
    code_subject: str
    code_exam_type: str
    is_complete: bool = False


class ExamenOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    titre: str
    date_examen: Optional[date] = None
    matiere_id: int
    classe_id: int
    professeur_id: Optional[int] = None
    matiere_nom: Optional[str] = None
    classe_nom: Optional[str] = None
    professeur_nom: Optional[str] = None
    created_at: datetime
    ressources: Optional[ExamResourcesOut] = None
    nb_copies: int = 0


# ---------------------------------------------------------------------------
# Copies
# ---------------------------------------------------------------------------

class CopieOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    examen_id: int
    etudiant_id: Optional[int] = None
    etudiant_nom: Optional[str] = None
    images_dir: str
    statut: str
    created_at: datetime


# ---------------------------------------------------------------------------
# Résultats
# ---------------------------------------------------------------------------

class ResultatOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    copie_id: int
    examen_id: int
    etudiant_id: Optional[int] = None
    etudiant_nom: Optional[str] = None
    statut: str
    message_erreur: Optional[str] = None
    student_data: Optional[Dict[str, Any]] = None
    qcm_result: Optional[Dict[str, Any]] = None
    redaction_result: Optional[Dict[str, Any]] = None
    code_result: Optional[Dict[str, Any]] = None
    sections_corrected: List[str] = []
    total_score: Optional[float] = None
    max_score: Optional[float] = None
    percentage: Optional[float] = None
    valide_par_professeur: bool = False
    note_ajustee: Optional[float] = None
    note_finale: Optional[float] = None
    commentaire_professeur: Optional[str] = None
    elapsed_seconds: Optional[float] = None
    created_at: datetime


class ValiderNoteRequest(BaseModel):
    commentaire: Optional[str] = None


class AjusterNoteRequest(BaseModel):
    nouvelle_note: float
    commentaire: Optional[str] = None


class DefinirRessourcesRequest(BaseModel):
    """Champs non-fichiers envoyés en JSON (multipart 'data' field)."""

    sections: Optional[List[str]] = None
    scoring_system: Optional[str] = None
    redaction_matiere: Optional[str] = None
    redaction_type_examen: Optional[str] = None
    redaction_contexte: Optional[str] = None
    code_language: Optional[str] = None
    code_exercise_type: Optional[str] = None
    code_title: Optional[str] = None
    code_function_name: Optional[str] = None
    code_subject: Optional[str] = None
    code_exam_type: Optional[str] = None


class StatistiquesOut(BaseModel):
    nombre_copies_corrigees: int
    moyenne: Optional[float] = None
    mediane: Optional[float] = None
    note_min: Optional[float] = None
    note_max: Optional[float] = None
    taux_echec_pipeline: float


class NoteEtudiantOut(BaseModel):
    examen: Optional[str] = None
    matiere: Optional[str] = None
    date_examen: Optional[str] = None
    note: Optional[float] = None
    note_max: Optional[float] = None
    pourcentage: Optional[float] = None
    valide_par_professeur: bool
    commentaire: Optional[str] = None
