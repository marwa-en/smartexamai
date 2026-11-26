from __future__ import annotations

import json
import tempfile
import uuid
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.deps import get_db, require_professeur
from app.schemas import (
    AjusterNoteRequest,
    DefinirRessourcesRequest,
    ExamenOut,
    ExamResourcesOut,
    ResultatOut,
    StatistiquesOut,
    ValiderNoteRequest,
)
from app.serializers import serialize_examen, serialize_resources, serialize_resultat
from core.exceptions import ExamenNotFoundError, PermissionDeniedError, ResultatNotFoundError
from modelss.user import User
from repositories.user_repository import UserRepository
from service.admin.examen_service import ExamenService
from service.professeur.professeur_service import ProfesseurService

router = APIRouter(
    prefix="/api/professeur",
    tags=["professeur"],
    dependencies=[Depends(require_professeur)],
)

# ============================================================================
# Configuration de sécurité des uploads
# ============================================================================

# Extensions autorisées pour les ressources pédagogiques
ALLOWED_RESOURCE_EXTENSIONS = {
    ".txt", ".pdf", ".csv", ".json",
    ".py", ".java", ".c", ".cpp", ".php",
    ".png", ".jpg", ".jpeg",
}

# Taille maximale par fichier (10 Mo)
MAX_RESOURCE_SIZE = 10 * 1024 * 1024


# ============================================================================
# Fonctions de validation
# ============================================================================

def _validate_resource_extension(filename: str) -> str:
    """Valide l'extension d'un fichier ressource."""
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_RESOURCE_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_RESOURCE_EXTENSIONS))
        raise HTTPException(
            status_code=415,
            detail=f"Extension '{ext}' non autorisée. Extensions acceptées : {allowed}",
        )
    return ext


async def _save_upload(upload: Optional[UploadFile], tmp_dir: Path) -> Optional[Path]:
    """Sauvegarde un fichier uploadé de manière sécurisée."""
    if upload is None or not upload.filename:
        return None

    # ✅ 1. Valider l'extension
    ext = _validate_resource_extension(upload.filename)

    # ✅ 2. Lire le contenu
    content = await upload.read()

    # ✅ 3. Vérifier la taille
    if len(content) > MAX_RESOURCE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"Le fichier '{upload.filename}' dépasse la taille maximale de 10 Mo.",
        )

    # ✅ 4. Nom de fichier généré côté serveur (jamais le nom original)
    safe_filename = f"{uuid.uuid4().hex}{ext}"
    dest = tmp_dir / safe_filename
    dest.write_bytes(content)

    return dest


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/examens", response_model=List[ExamenOut])
def mes_examens(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_professeur),
):
    examens = ExamenService(db).list_examens()
    mine = [e for e in examens if e.professeur_id == current_user.id]
    return [serialize_examen(e) for e in mine]


@router.post("/examens/{examen_id}/ressources", response_model=ExamResourcesOut)
async def definir_ressources(
    examen_id: int,
    data: str = Form(default="{}"),
    consignes: Optional[UploadFile] = None,
    corrige: Optional[UploadFile] = None,
    unit_tests: Optional[UploadFile] = None,
    code_consignes: Optional[UploadFile] = None,
    cours: Optional[UploadFile] = None,
    bareme: Optional[UploadFile] = None,
    qcm_template: Optional[UploadFile] = None,
    qcm_answer_key: Optional[UploadFile] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_professeur),
):
    """Dépose/mets à jour les ressources pédagogiques d'un examen."""
    try:
        payload = DefinirRessourcesRequest.model_validate(json.loads(data))
    except (json.JSONDecodeError, ValueError):
        raise HTTPException(status_code=400, detail="Champ 'data' JSON invalide.")

    tmp_dir = Path(tempfile.mkdtemp(prefix="smartexam_res_"))
    saved: List[Path] = []

    try:
        consignes_p = await _save_upload(consignes, tmp_dir)
        corrige_p = await _save_upload(corrige, tmp_dir)
        unit_tests_p = await _save_upload(unit_tests, tmp_dir)
        code_consignes_p = await _save_upload(code_consignes, tmp_dir)
        cours_p = await _save_upload(cours, tmp_dir)
        bareme_p = await _save_upload(bareme, tmp_dir)
        qcm_template_p = await _save_upload(qcm_template, tmp_dir)
        qcm_answer_key_p = await _save_upload(qcm_answer_key, tmp_dir)
        saved = [p for p in [
            consignes_p, corrige_p, unit_tests_p, code_consignes_p,
            cours_p, bareme_p, qcm_template_p, qcm_answer_key_p,
        ] if p is not None]

        metadata = payload.model_dump(exclude_unset=True, exclude={"sections", "scoring_system"})

        try:
            ressources = ProfesseurService(db).definir_ressources(
                examen_id=examen_id,
                professeur_id=current_user.id,
                consignes_file=consignes_p,
                corrige_file=corrige_p,
                unit_tests_file=unit_tests_p,
                code_consignes_file=code_consignes_p,
                cours_file=cours_p,
                bareme_file=bareme_p,
                qcm_template_file=qcm_template_p,
                qcm_answer_key_file=qcm_answer_key_p,
                sections=payload.sections,
                scoring_system=payload.scoring_system,
                **metadata,
            )
        except ExamenNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        except PermissionDeniedError as exc:
            raise HTTPException(status_code=403, detail=str(exc))

        db.flush()
        db.refresh(ressources)
        return serialize_resources(ressources)

    finally:
        for p in saved:
            p.unlink(missing_ok=True)
        try:
            tmp_dir.rmdir()
        except OSError:
            pass


@router.get("/examens/{examen_id}/resultats", response_model=List[ResultatOut])
def consulter_resultats(
    examen_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_professeur),
):
    try:
        resultats = ProfesseurService(db).consulter_resultats(examen_id, current_user.id)
    except ExamenNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except PermissionDeniedError as exc:
        raise HTTPException(status_code=403, detail=str(exc))

    user_repo = UserRepository(db)
    out = []
    for r in resultats:
        etu = user_repo.get(r.etudiant_id) if r.etudiant_id else None
        out.append(serialize_resultat(r, etu))
    return out


@router.get("/examens/{examen_id}/statistiques", response_model=StatistiquesOut)
def statistiques(
    examen_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_professeur),
):
    try:
        stats = ProfesseurService(db).statistiques_examen(examen_id, current_user.id)
    except ExamenNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except PermissionDeniedError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    return StatistiquesOut(**stats)


@router.post("/resultats/{resultat_id}/valider", response_model=ResultatOut)
def valider_note(
    resultat_id: int,
    payload: ValiderNoteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_professeur),
):
    try:
        resultat = ProfesseurService(db).valider_note(
            resultat_id, current_user.id, payload.commentaire
        )
    except ResultatNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except PermissionDeniedError as exc:
        raise HTTPException(status_code=403, detail=str(exc))

    db.flush()
    db.refresh(resultat)
    user_repo = UserRepository(db)
    etu = user_repo.get(resultat.etudiant_id) if resultat.etudiant_id else None
    return serialize_resultat(resultat, etu)


@router.post("/resultats/{resultat_id}/ajuster", response_model=ResultatOut)
def ajuster_note(
    resultat_id: int,
    payload: AjusterNoteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_professeur),
):
    try:
        resultat = ProfesseurService(db).ajuster_note(
            resultat_id, current_user.id, payload.nouvelle_note, payload.commentaire
        )
    except ResultatNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except PermissionDeniedError as exc:
        raise HTTPException(status_code=403, detail=str(exc))

    db.flush()
    db.refresh(resultat)
    user_repo = UserRepository(db)
    etu = user_repo.get(resultat.etudiant_id) if resultat.etudiant_id else None
    return serialize_resultat(resultat, etu)