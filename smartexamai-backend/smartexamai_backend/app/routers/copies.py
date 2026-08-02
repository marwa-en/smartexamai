from __future__ import annotations

import tempfile
import uuid
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.deps import get_current_user, get_db, require_admin
from app.schemas import CopieOut
from app.serializers import serialize_copie
from core.exceptions import CopieNotFoundError, ExamenNotFoundError
from modelss.user import User
from service.admin.copie_service import CopieService

router = APIRouter(prefix="/api/admin/copies", tags=["admin:copies"], dependencies=[Depends(require_admin)])


@router.get("/by-examen/{examen_id}", response_model=List[CopieOut])
def list_copies_by_examen(examen_id: int, db: Session = Depends(get_db)):
    return [serialize_copie(c) for c in CopieService(db).list_copies_by_examen(examen_id)]


@router.get("/{copie_id}", response_model=CopieOut)
def get_copie(copie_id: int, db: Session = Depends(get_db)):
    try:
        copie = CopieService(db).get_copie(copie_id)
    except CopieNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return serialize_copie(copie)


@router.post("", response_model=CopieOut, status_code=201)
async def deposer_copie(
    examen_id: int = Form(...),
    etudiant_id: Optional[int] = Form(default=None),
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Dépose les pages scannées (images) d'une copie d'étudiant pour un examen."""
    if not files:
        raise HTTPException(status_code=400, detail="Aucun fichier fourni.")

    tmp_dir = Path(tempfile.mkdtemp(prefix="smartexam_upload_"))
    saved_paths: List[Path] = []
    try:
        for upload in files:
            suffix = Path(upload.filename or "page.png").suffix or ".png"
            dest = tmp_dir / f"{uuid.uuid4().hex}{suffix}"
            content = await upload.read()
            dest.write_bytes(content)
            saved_paths.append(dest)

        try:
            copie = CopieService(db).deposer_copie(
                examen_id=examen_id,
                image_paths=saved_paths,
                etudiant_id=etudiant_id,
                deposee_par_admin_id=current_user.id,
            )
        except ExamenNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))

        db.flush()
        db.refresh(copie)
        return serialize_copie(copie)
    finally:
        for p in saved_paths:
            p.unlink(missing_ok=True)
        try:
            tmp_dir.rmdir()
        except OSError:
            pass
