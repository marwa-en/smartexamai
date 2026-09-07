from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.deps import get_db, require_admin, require_admin_or_prof, get_current_user
from app.schemas import AssignProfesseurRequest, ExamenCreate, ExamenOut, ExamenUpdate
from app.serializers import serialize_examen
from core.exceptions import ExamenNotFoundError
from modelss.enums import RoleUtilisateur
from modelss.user import User
from service.admin.examen_service import ExamenService

router = APIRouter(prefix="/api/admin/examens", tags=["admin:examens"])


# ============================================================================
# LISTE DES EXAMENS
# ============================================================================

@router.get(
    "",
    response_model=List[ExamenOut],
    dependencies=[Depends(require_admin_or_prof)],
)
def list_examens(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Liste les examens.
    - Admin : voit tous les examens
    - Professeur : voit uniquement SES examens
    """
    if current_user.role == RoleUtilisateur.PROFESSEUR.value:
        # ✅ RBAC : un professeur ne voit que ses propres examens
        examens = ExamenService(db).list_examens_by_professeur(current_user.id)
    else:
        examens = ExamenService(db).list_examens()

    return [serialize_examen(e) for e in examens]


@router.get(
    "/by-classe/{classe_id}",
    response_model=List[ExamenOut],
    dependencies=[Depends(require_admin_or_prof)],
)
def list_examens_by_classe(
    classe_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Liste les examens d'une classe.
    - Admin : voit tous les examens de la classe
    - Professeur : voit uniquement ses examens dans cette classe
    """
    examens = ExamenService(db).list_examens_by_classe(classe_id)

    if current_user.role == RoleUtilisateur.PROFESSEUR.value:
        # ✅ RBAC : filtrer uniquement les examens du professeur
        examens = [e for e in examens if e.professeur_id == current_user.id]

    return [serialize_examen(e) for e in examens]


# ============================================================================
# CRUD EXAMENS
# ============================================================================

@router.post(
    "",
    response_model=ExamenOut,
    status_code=201,
    dependencies=[Depends(require_admin)],
)
def create_examen(payload: ExamenCreate, db: Session = Depends(get_db)):
    examen = ExamenService(db).create_examen(
        titre=payload.titre,
        matiere_id=payload.matiere_id,
        classe_id=payload.classe_id,
        professeur_id=payload.professeur_id,
        date_examen=payload.date_examen,
    )
    db.flush()
    db.refresh(examen)
    return serialize_examen(examen)


@router.get(
    "/{examen_id}",
    response_model=ExamenOut,
    dependencies=[Depends(require_admin_or_prof)],
)
def get_examen(
    examen_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Récupère un examen par ID.
    ✅ Vérifie que le professeur a bien le droit d'y accéder.
    """
    try:
        examen = ExamenService(db).get_examen(examen_id)
    except ExamenNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    # ✅ RBAC : vérifier que le professeur possède cet examen
    if current_user.role == RoleUtilisateur.PROFESSEUR.value:
        if examen.professeur_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="Accès refusé : cet examen ne vous est pas assigné.",
            )

    return serialize_examen(examen)


@router.patch(
    "/{examen_id}",
    response_model=ExamenOut,
    dependencies=[Depends(require_admin)],
)
def update_examen(
    examen_id: int,
    payload: ExamenUpdate,
    db: Session = Depends(get_db),
):
    fields = payload.model_dump(exclude_unset=True)
    try:
        examen = ExamenService(db).update_examen(examen_id, **fields)
    except ExamenNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    db.flush()
    db.refresh(examen)
    return serialize_examen(examen)


@router.delete(
    "/{examen_id}",
    status_code=204,
    dependencies=[Depends(require_admin)],
)
def delete_examen(examen_id: int, db: Session = Depends(get_db)):
    try:
        ExamenService(db).delete_examen(examen_id)
    except ExamenNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post(
    "/{examen_id}/assign-professeur",
    response_model=ExamenOut,
    dependencies=[Depends(require_admin)],
)
def assign_professeur(
    examen_id: int,
    payload: AssignProfesseurRequest,
    db: Session = Depends(get_db),
):
    try:
        examen = ExamenService(db).assign_professeur(examen_id, payload.professeur_id)
    except ExamenNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    db.flush()
    db.refresh(examen)
    return serialize_examen(examen)