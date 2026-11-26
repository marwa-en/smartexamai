"""
SmartExamAI — Engine et gestion des sessions SQLAlchemy.

Fournit `session_scope()`, un context manager transactionnel à utiliser
par toutes les couches services/repositories : commit automatique en cas
de succès, rollback automatique en cas d'exception.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from configss.settings import settings

engine = create_engine(
    settings.database_url,
    echo=settings.echo_sql,
    future=True,
    # Nécessaire pour SQLite utilisé depuis plusieurs threads/services
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


@contextmanager
def session_scope() -> Iterator[Session]:
    """Fournit une session transactionnelle.

    Usage :
        with session_scope() as db:
            db.add(obj)
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
