from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.deps import get_db, require_admin
from app.schemas import ResultatOut
from app.serializers import serialize_resultat
from core.exceptions import (
    CopieAlreadyProcessingError,
    CopieNotFoundError,
    CorrectionPipelineError,
    ExamenNotFoundError,
    ExamResourcesIncompleteError,
)
from service.admin.correction_service import CorrectionService
from repositories.user_repository import UserRepository

router = APIRouter(prefix="/api/admin/correction", tags=["admin:correction"], dependencies=[Depends(require_admin)])


def _to_out(db: Session, resultat) -> ResultatOut:
    etudiant = UserRepository(db).get(resultat.etudiant_id) if resultat.etudiant_id else None
    return serialize_resultat(resultat, etudiant)


@router.post("/copies/{copie_id}", response_model=ResultatOut)
def lancer_correction(copie_id: int, db: Session = Depends(get_db)):
    try:
        resultat = CorrectionService(db).lancer_correction(copie_id)
    except CopieNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except CopieAlreadyProcessingError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ExamenNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ExamResourcesIncompleteError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except CorrectionPipelineError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    db.flush()
    db.refresh(resultat)
    return _to_out(db, resultat)


@router.post("/examens/{examen_id}/lot", response_model=List[ResultatOut])
def lancer_correction_lot(examen_id: int, db: Session = Depends(get_db)):
    try:
        resultats = CorrectionService(db).lancer_correction_lot(examen_id)
    except ExamResourcesIncompleteError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except CorrectionPipelineError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    db.flush()
    for r in resultats:
        db.refresh(r)
    return [_to_out(db, r) for r in resultats]
