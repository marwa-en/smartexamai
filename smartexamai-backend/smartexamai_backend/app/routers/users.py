from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.deps import get_db, require_admin
from app.schemas import UserCreate, UserOut, UserUpdate
from core.exceptions import DuplicateEntityError, UserNotFoundError
from modelss.enums import RoleUtilisateur
from service.admin.user_management_service import UserManagementService

router = APIRouter(prefix="/api/admin/users", tags=["admin:users"], dependencies=[Depends(require_admin)])


@router.get("", response_model=List[UserOut])
def list_users(role: Optional[str] = Query(default=None), db: Session = Depends(get_db)):
    role_enum = RoleUtilisateur(role) if role else None
    users = UserManagementService(db).list_users(role_enum)
    return [UserOut.model_validate(u) for u in users]


@router.post("", response_model=UserOut, status_code=201)
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    try:
        user = UserManagementService(db).create_user(
            username=payload.username,
            email=payload.email,
            password=payload.password,
            role=RoleUtilisateur(payload.role),
            nom=payload.nom,
            prenom=payload.prenom,
            cne=payload.cne,
            classe_id=payload.classe_id,
        )
    except DuplicateEntityError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    db.flush()
    db.refresh(user)
    return UserOut.model_validate(user)


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: int, db: Session = Depends(get_db)):
    try:
        user = UserManagementService(db).get_user(user_id)
    except UserNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return UserOut.model_validate(user)


@router.patch("/{user_id}", response_model=UserOut)
def update_user(user_id: int, payload: UserUpdate, db: Session = Depends(get_db)):
    fields = payload.model_dump(exclude_unset=True)
    try:
        user = UserManagementService(db).update_user(user_id, **fields)
    except UserNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    db.flush()
    db.refresh(user)
    return UserOut.model_validate(user)


@router.post("/{user_id}/deactivate", response_model=UserOut)
def deactivate_user(user_id: int, db: Session = Depends(get_db)):
    try:
        user = UserManagementService(db).deactivate_user(user_id)
    except UserNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return UserOut.model_validate(user)


@router.post("/{user_id}/reactivate", response_model=UserOut)
def reactivate_user(user_id: int, db: Session = Depends(get_db)):
    try:
        user = UserManagementService(db).reactivate_user(user_id)
    except UserNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return UserOut.model_validate(user)
