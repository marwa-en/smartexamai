"""
SmartExamAI — Router d'authentification.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.deps import get_current_user, get_db
from app.schemas import LoginRequest, TokenResponse, UserOut
from app.security_jwt import create_access_token
from app.rate_limit import login_limiter
from modelss.user import User
from repositories.user_repository import UserRepository
from core.security import hash_password, verify_password
from typing import Optional
from app.security_refresh import (
    create_refresh_token,
    rotate_refresh_token,
    revoke_refresh_token,
    revoke_all_for_user,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Configuration du verrouillage
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15


# ============================================================================
# Schémas locaux
# ============================================================================

class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=12)


class ChangePasswordResponse(BaseModel):
    detail: str


# ============================================================================
# Politique de mot de passe
# ============================================================================

def validate_password_strength(password: str) -> list[str]:
    errors = []
    if len(password) < 12:
        errors.append("Le mot de passe doit contenir au moins 12 caractères.")
    if not re.search(r"[A-Z]", password):
        errors.append("Le mot de passe doit contenir au moins une majuscule.")
    if not re.search(r"[a-z]", password):
        errors.append("Le mot de passe doit contenir au moins une minuscule.")
    if not re.search(r"\d", password):
        errors.append("Le mot de passe doit contenir au moins un chiffre.")
    return errors


# ============================================================================
# Helpers de verrouillage
# ============================================================================

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _is_locked(user: User) -> bool:
    if user.locked_until is None:
        return False
    locked_until = user.locked_until
    if locked_until.tzinfo is None:
        locked_until = locked_until.replace(tzinfo=timezone.utc)
    return locked_until > _utcnow()


def _register_failed_login(db: Session, user: User) -> None:
    user.failed_login_count = (user.failed_login_count or 0) + 1

    if user.failed_login_count >= MAX_FAILED_ATTEMPTS:
        user.locked_until = _utcnow() + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
        user.failed_login_count = 0

    db.commit()


def _register_successful_login(db: Session, user: User) -> None:
    user.failed_login_count = 0
    user.locked_until = None
    db.commit()


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Connexion utilisateur avec protection brute-force."""

    # 1. Rate limiting par IP
    client_ip = request.client.host if request.client else "unknown"
    rate_limit_key = f"login:{client_ip}"

    if not login_limiter.is_allowed(rate_limit_key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Trop de tentatives de connexion. Réessayez dans quelques minutes.",
        )

    # 2. Chercher l'utilisateur
    user = UserRepository(db).get_by_username(payload.username)

    if user is None:
        # Ne pas révéler si le username existe ou non
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nom d'utilisateur ou mot de passe incorrect.",
        )

    # 3. Vérifier si le compte est verrouillé
    if _is_locked(user):
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=f"Compte temporairement verrouillé. Réessayez dans {LOCKOUT_DURATION_MINUTES} minutes.",
        )

    # 4. Vérifier le mot de passe
    if not verify_password(payload.password, user.password_hash):
        _register_failed_login(db, user)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nom d'utilisateur ou mot de passe incorrect.",
        )

    # 5. Vérifier si le compte est actif
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ce compte a été désactivé.",
        )

    # 6. Succès : réinitialiser les compteurs
    _register_successful_login(db, user)
    login_limiter.reset(rate_limit_key)

    # 7. Générer le token
    token = create_access_token(user_id=user.id, username=user.username, role=user.role)

    # ✅ Émettre un refresh token (nouvelle famille de session)
    refresh = create_refresh_token(
        db,
        user,
        user_agent=request.headers.get("user-agent"),
        ip=request.client.host if request.client else None,
    )

    return TokenResponse(
        access_token=token,
        user=UserOut.model_validate(user),
        must_change_password=getattr(user, "must_change_password", False),
        refresh_token=refresh,
    )

@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)) -> UserOut:
    return UserOut.model_validate(current_user)


@router.post(
    "/change-password",
    response_model=ChangePasswordResponse,
    summary="Changer le mot de passe de l'utilisateur connecté",
)
def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mot de passe actuel incorrect.",
        )

    errors = validate_password_strength(payload.new_password)
    if errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=" ".join(errors),
        )

    if verify_password(payload.new_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le nouveau mot de passe doit être différent de l'actuel.",
        )

    current_user.password_hash = hash_password(payload.new_password)
    current_user.must_change_password = False
        # ✅ Sécurité : un changement de mot de passe tue toutes les sessions
    revoke_all_for_user(db, current_user.id)
    db.commit()

    return {"detail": "Mot de passe mis à jour avec succès."}
class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: Optional[str] = None


@router.post("/refresh", response_model=TokenResponse)
def refresh_tokens(
    payload: RefreshRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Échange un refresh token valide contre une nouvelle paire de tokens."""
    try:
        user, new_refresh = rotate_refresh_token(
            db,
            payload.refresh_token,
            user_agent=request.headers.get("user-agent"),
            ip=request.client.host if request.client else None,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        )

    token = create_access_token(user_id=user.id, username=user.username, role=user.role)

    return TokenResponse(
        access_token=token,
        user=UserOut.model_validate(user),
        must_change_password=getattr(user, "must_change_password", False),
        refresh_token=new_refresh,
    )


@router.post("/logout")
def logout(
    payload: LogoutRequest,
    db: Session = Depends(get_db),
):
    """Logout serveur-side : révoque le refresh token fourni."""
    if payload.refresh_token:
        revoke_refresh_token(db, payload.refresh_token)
    return {"detail": "Déconnecté."}