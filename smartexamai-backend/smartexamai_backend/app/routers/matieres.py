from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.deps import get_db, require_admin
from app.schemas import MatiereCreate, MatiereOut, MatiereUpdate
from core.exceptions import MatiereNotFoundError
from service.admin.matiere_service import MatiereService

router = APIRouter(prefix="/api/admin/matieres", tags=["admin:matieres"], dependencies=[Depends(require_admin)])


@router.get("", response_model=List[MatiereOut])
def list_matieres(db: Session = Depends(get_db)):
    return [MatiereOut.model_validate(m) for m in MatiereService(db).list_matieres()]


@router.post("", response_model=MatiereOut, status_code=201)
def create_matiere(payload: MatiereCreate, db: Session = Depends(get_db)):
    matiere = MatiereService(db).create_matiere(nom=payload.nom, code=payload.code)
    db.flush()
    db.refresh(matiere)
    return MatiereOut.model_validate(matiere)


@router.get("/{matiere_id}", response_model=MatiereOut)
def get_matiere(matiere_id: int, db: Session = Depends(get_db)):
    try:
        matiere = MatiereService(db).get_matiere(matiere_id)
    except MatiereNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return MatiereOut.model_validate(matiere)


@router.patch("/{matiere_id}", response_model=MatiereOut)
def update_matiere(matiere_id: int, payload: MatiereUpdate, db: Session = Depends(get_db)):
    fields = payload.model_dump(exclude_unset=True)
    try:
        matiere = MatiereService(db).update_matiere(matiere_id, **fields)
    except MatiereNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    db.flush()
    db.refresh(matiere)
    return MatiereOut.model_validate(matiere)


@router.delete("/{matiere_id}", status_code=204)
def delete_matiere(matiere_id: int, db: Session = Depends(get_db)):
    try:
        MatiereService(db).delete_matiere(matiere_id)
    except MatiereNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
