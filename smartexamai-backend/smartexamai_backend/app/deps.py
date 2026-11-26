"""
SmartExamAI — Dépendances FastAPI communes.

- get_db : fournit une Session SQLAlchemy par requête (commit si succès,
  rollback si exception), sur le même modèle que db.session.session_scope.
- get_current_user : décode le JWT et charge l'utilisateur associé.
- require_role(...) : fabrique de dépendances pour restreindre un
  endpoint à un ou plusieurs rôles.
"""
from __future__ import annotations

from typing import Iterator

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.security_jwt import InvalidTokenError, decode_access_token, password_fingerprint
from app.audit import log_event
from db.session import SessionLocal
from modelss.enums import RoleUtilisateur
from modelss.user import User
from repositories.user_repository import UserRepository

bearer_scheme = HTTPBearer(auto_error=False)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# Routes accessibles même quand le changement de mot de passe est obligatoire
_PWD_CHANGE_ALLOWED = ("/api/auth/change-password", "/api/auth/me", "/api/auth/logout")


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentification requise.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_access_token(credentials.credentials)
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide ou expiré.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # ✅ F-01 : un jeton signé mais mal formé ne doit jamais provoquer un HTTP 500
    try:
        user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide ou expiré.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = UserRepository(db).get(user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Compte introuvable ou désactivé.",
        )
    # ✅ F-11 : le jeton doit correspondre au mot de passe ACTUEL (changement = révocation)
    if payload.get("pwv") != password_fingerprint(user.password_hash):
        log_event("auth.stale_token", user_id=user.id, ip=request.client.host if request.client else None)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide ou expiré.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # ✅ F-12 : changement de mot de passe obligatoire avant toute autre action
    if getattr(user, "must_change_password", False) and request.url.path not in _PWD_CHANGE_ALLOWED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Changement de mot de passe obligatoire avant de continuer.",
        )
    return user


def require_role(*roles: RoleUtilisateur):
    """Fabrique une dépendance qui vérifie que l'utilisateur courant
    possède l'un des rôles autorisés."""
    allowed = {r.value for r in roles}

    def _dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Accès refusé : rôle insuffisant pour cette action.",
            )
        return current_user

    return _dependency


require_admin = require_role(RoleUtilisateur.ADMIN)
require_professeur = require_role(RoleUtilisateur.PROFESSEUR)
require_etudiant = require_role(RoleUtilisateur.ETUDIANT)
require_admin_or_prof = require_role(RoleUtilisateur.ADMIN, RoleUtilisateur.PROFESSEUR)
