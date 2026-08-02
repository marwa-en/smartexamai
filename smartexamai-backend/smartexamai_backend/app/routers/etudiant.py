from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.deps import get_db, require_etudiant
from app.schemas import NoteEtudiantOut
from modelss.user import User
from service.etudiant.etudiant_service import EtudiantService

router = APIRouter(prefix="/api/etudiant", tags=["etudiant"], dependencies=[Depends(require_etudiant)])


@router.get("/notes", response_model=List[NoteEtudiantOut])
def consulter_notes(db: Session = Depends(get_db), current_user: User = Depends(require_etudiant)):
    notes = EtudiantService(db).consulter_notes(current_user.id)
    return [NoteEtudiantOut(**n) for n in notes]


@router.get("/releve")
def telecharger_releve(db: Session = Depends(get_db), current_user: User = Depends(require_etudiant)):
    path = EtudiantService(db).telecharger_releve(current_user.id)
    media_type = "application/pdf" if path.suffix == ".pdf" else "text/plain"
    return FileResponse(path=str(path), media_type=media_type, filename=path.name)
