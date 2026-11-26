"""
SmartExamAI — Génération et vérification des tokens JWT.

Ajoute une couche d'authentification HTTP (Bearer token) au-dessus du
hachage de mot de passe déjà présent dans core/security.py, sans le
modifier.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

import jwt

# Clé de signature JWT — à définir en production via variable d'environnement.
JWT_SECRET = os.environ.get("SMARTEXAM_JWT_SECRET", "dev-secret-change-me-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.environ.get("SMARTEXAM_JWT_EXPIRE_MINUTES", "480"))  # 8h


class InvalidTokenError(Exception):
    pass


def create_access_token(*, user_id: int, username: str, role: str) -> str:
    now = datetime.now(timezone.utc)
    payload: Dict[str, Any] = {
        "sub": str(user_id),
        "username": username,
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=JWT_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> Dict[str, Any]:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError as exc:
        raise InvalidTokenError(str(exc)) from exc
