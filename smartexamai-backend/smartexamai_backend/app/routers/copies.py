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

router = APIRouter(
    prefix="/api/admin/copies",
    tags=["admin:copies"],
    dependencies=[Depends(require_admin)],
)

# ============================================================================
# Configuration de sécurité des uploads
# ============================================================================

# Extensions autorisées pour les copies scannées
ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".pdf"}

# Taille maximale par fichier (20 Mo)
MAX_IMAGE_SIZE = 20 * 1024 * 1024

# Nombre maximal de pages par copie
MAX_PAGES = 50


# ============================================================================
# Fonctions de validation
# ============================================================================

def _validate_image_extension(filename: str) -> str:
    """Valide l'extension d'un fichier image et retourne l'extension normalisée."""
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_IMAGE_EXTENSIONS))
        raise HTTPException(
            status_code=415,
            detail=f"Extension '{ext}' non autorisée. Extensions acceptées : {allowed}",
        )
    return ext


def _is_valid_image(content: bytes) -> bool:
    """Vérifie si le contenu correspond à une image valide via magic bytes."""
    if len(content) < 4:
        return False

    # PNG
    if content[:8] == b"\x89PNG\r\n\x1a\n":
        return True
    # JPEG
    if content[:2] == b"\xff\xd8":
        return True
    # TIFF
    if content[:4] == b"II\x2a\x00" or content[:4] == b"MM\x00\x2a":
        return True
    # BMP
    if content[:2] == b"BM":
        return True
    # PDF
    if content[:4] == b"%PDF":
        return True

    return False


# ============================================================================
# Endpoints
# ============================================================================

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

    # ✅ 1. Vérifier qu'il y a des fichiers
    if not files:
        raise HTTPException(status_code=400, detail="Aucun fichier fourni.")

    # ✅ 2. Vérifier le nombre maximum de pages
    if len(files) > MAX_PAGES:
        raise HTTPException(
            status_code=400,
            detail=f"Nombre maximum de pages dépassé ({MAX_PAGES}).",
        )

    tmp_dir = Path(tempfile.mkdtemp(prefix="smartexam_upload_"))
    saved_paths: List[Path] = []

    try:
        for upload in files:
            # ✅ 3. Valider l'extension
            ext = _validate_image_extension(upload.filename or "page.png")

            # ✅ 4. Lire le contenu
            content = await upload.read()

            # ✅ 5. Vérifier la taille
            if len(content) > MAX_IMAGE_SIZE:
                raise HTTPException(
                    status_code=413,
                    detail=f"Le fichier '{upload.filename}' dépasse la taille maximale de 20 Mo.",
                )

            # ✅ 6. Vérifier que c'est bien une image (magic bytes)
            if not _is_valid_image(content):
                raise HTTPException(
                    status_code=415,
                    detail=f"Le fichier '{upload.filename}' n'est pas une image valide.",
                )

            # ✅ 7. Nom de fichier généré côté serveur (jamais le nom original)
            safe_filename = f"{uuid.uuid4().hex}{ext}"
            dest = tmp_dir / safe_filename
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