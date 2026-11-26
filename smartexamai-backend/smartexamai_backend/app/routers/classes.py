from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.deps import get_db, require_admin
from app.schemas import ClasseCreate, ClasseOut, ClasseUpdate, UserOut
from app.serializers import serialize_classe
from core.exceptions import ClasseNotFoundError
from service.admin.classe_service import ClasseService

router = APIRouter(prefix="/api/admin/classes", tags=["admin:classes"], dependencies=[Depends(require_admin)])


@router.get("", response_model=List[ClasseOut])
def list_classes(db: Session = Depends(get_db)):
    classes = ClasseService(db).list_classes()
    return [serialize_classe(c) for c in classes]


@router.post("", response_model=ClasseOut, status_code=201)
def create_classe(payload: ClasseCreate, db: Session = Depends(get_db)):
    classe = ClasseService(db).create_classe(
        nom=payload.nom, niveau=payload.niveau, annee_scolaire=payload.annee_scolaire
    )
    db.flush()
    db.refresh(classe)
    return serialize_classe(classe)


@router.get("/{classe_id}", response_model=ClasseOut)
def get_classe(classe_id: int, db: Session = Depends(get_db)):
    try:
        classe = ClasseService(db).get_classe(classe_id)
    except ClasseNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return serialize_classe(classe)


@router.patch("/{classe_id}", response_model=ClasseOut)
def update_classe(classe_id: int, payload: ClasseUpdate, db: Session = Depends(get_db)):
    fields = payload.model_dump(exclude_unset=True)
    try:
        classe = ClasseService(db).update_classe(classe_id, **fields)
    except ClasseNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    db.flush()
    db.refresh(classe)
    return serialize_classe(classe)


@router.delete("/{classe_id}", status_code=204)
def delete_classe(classe_id: int, db: Session = Depends(get_db)):
    try:
        ClasseService(db).delete_classe(classe_id)
    except ClasseNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/{classe_id}/etudiants", response_model=List[UserOut])
def list_etudiants(classe_id: int, db: Session = Depends(get_db)):
    try:
        etudiants = ClasseService(db).list_etudiants(classe_id)
    except ClasseNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return [UserOut.model_validate(e) for e in etudiants]
