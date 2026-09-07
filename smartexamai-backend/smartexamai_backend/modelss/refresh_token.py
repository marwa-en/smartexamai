"""
SmartExamAI — Modèle RefreshToken (sessions avec rotation + révocation).

Sécurité :
- Le token brut n'est JAMAIS stocké : seule son empreinte SHA-256 l'est.
- family_id permet la rotation et la détection de réutilisation (vol).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    # Empreinte SHA-256 du token brut (jamais stocké en clair)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)

    # Famille de tokens : rotation + détection de réutilisation
    family_id: Mapped[str] = mapped_column(String(36), index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Métadonnées d'audit
    user_agent: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<RefreshToken user={self.user_id} revoked={self.revoked_at is not None}>"