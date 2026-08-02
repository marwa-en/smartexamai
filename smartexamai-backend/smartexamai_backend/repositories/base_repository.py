"""SmartExamAI — Repository générique réutilisable par toutes les entités."""
from __future__ import annotations

from typing import Generic, List, Optional, Type, TypeVar

from sqlalchemy.orm import Session

ModelT = TypeVar("ModelT")


class BaseRepository(Generic[ModelT]):
    """Encapsule les opérations CRUD élémentaires pour un modèle donné."""

    model: Type[ModelT]

    def __init__(self, db: Session):
        self.db = db

    def get(self, entity_id: int) -> Optional[ModelT]:
        return self.db.get(self.model, entity_id)

    def list_all(self) -> List[ModelT]:
        return list(self.db.query(self.model).all())

    def add(self, entity: ModelT) -> ModelT:
        self.db.add(entity)
        self.db.flush()
        return entity

    def delete(self, entity: ModelT) -> None:
        self.db.delete(entity)
        self.db.flush()
