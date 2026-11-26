"""
SmartExamAI — Gestion des refresh tokens (rotation + révocation).

Principes :
- Le refresh token brut n'est JAMAIS stocké : seule son empreinte SHA-256 l'est.
- Rotation à chaque usage : l'ancien token est révoqué, un nouveau est émis.
- Détection de réutilisation : si un token déjà révoqué est rejoué,
  toute la famille est révoquée (signe de vol de token).
"""
from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from configss.settings import settings
from modelss.refresh_token import RefreshToken
from modelss.user import User


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _hash_token(raw_token: str) -> str:
    """Empreinte SHA-256 du token brut."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def create_refresh_token(
    db: Session,
    user: User,
    family_id: Optional[str] = None,
    user_agent: Optional[str] = None,
    ip: Optional[str] = None,
) -> str:
    """Crée un refresh token et retourne le token BRUT (à envoyer au client)."""
    raw_token = secrets.token_urlsafe(48)

    token = RefreshToken(
        user_id=user.id,
        token_hash=_hash_token(raw_token),
        family_id=family_id or str(uuid.uuid4()),
        expires_at=_utcnow() + timedelta(days=settings.refresh_token_expire_days),
        user_agent=(user_agent or "")[:200] or None,
        ip=(ip or "")[:45] or None,
    )
    db.add(token)
    db.commit()
    return raw_token


def rotate_refresh_token(
    db: Session,
    raw_token: str,
    user_agent: Optional[str] = None,
    ip: Optional[str] = None,
) -> Tuple[User, str]:
    """
    Valide un refresh token et effectue la rotation.

    Retourne (user, nouveau_token_brut).
    Lève ValueError si token inconnu / expiré / révoqué.
    """
    token = db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == _hash_token(raw_token))
    )

    if token is None:
        raise ValueError("Refresh token inconnu.")

    # ⚠️ DÉTECTION DE VOL : un token déjà révoqué qui est rejoué
    # => on révoque TOUTE la famille par sécurité.
    if token.revoked_at is not None:
        _revoke_family(db, token.family_id)
        raise ValueError("Refresh token réutilisé : toutes les sessions ont été révoquées.")

    # Expiration
    expires_at = token.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= _utcnow():
        token.revoked_at = _utcnow()
        db.commit()
        raise ValueError("Refresh token expiré.")

    user = db.get(User, token.user_id)
    if user is None or not user.is_active:
        raise ValueError("Utilisateur introuvable ou désactivé.")

    # Rotation : révoquer l'ancien + émettre un nouveau dans la même famille
    token.revoked_at = _utcnow()
    db.commit()

    new_raw = create_refresh_token(
        db, user, family_id=token.family_id, user_agent=user_agent, ip=ip
    )
    return user, new_raw


def revoke_refresh_token(db: Session, raw_token: str) -> None:
    """Révoque un refresh token précis (logout d'un appareil)."""
    token = db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == _hash_token(raw_token))
    )
    if token is not None and token.revoked_at is None:
        token.revoked_at = _utcnow()
        db.commit()


def revoke_all_for_user(db: Session, user_id: int) -> None:
    """Révoque TOUTES les sessions d'un utilisateur (logout global)."""
    for token in db.scalars(
        select(RefreshToken).where(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked_at.is_(None),
        )
    ):
        token.revoked_at = _utcnow()
    db.commit()


def _revoke_family(db: Session, family_id: str) -> None:
    """Révoque toute une famille de tokens (détection de vol)."""
    for token in db.scalars(
        select(RefreshToken).where(
            RefreshToken.family_id == family_id,
            RefreshToken.revoked_at.is_(None),
        )
    ):
        token.revoked_at = _utcnow()
    db.commit()