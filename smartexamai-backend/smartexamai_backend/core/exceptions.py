"""
SmartExamAI — Exceptions métier.

Ces exceptions sont indépendantes de celles du pipeline IA
(ai_pipeline.orchestrator.OrchestratorError et ses sous-classes),
qui restent internes à la couche d'intégration.
"""
from __future__ import annotations


class SmartExamError(Exception):
    """Racine de toutes les erreurs métier du backend."""


# --- Erreurs génériques ---

class NotFoundError(SmartExamError):
    """Entité introuvable en base."""


class ValidationErrorSmartExam(SmartExamError):
    """Donnée d'entrée invalide."""


class PermissionDeniedError(SmartExamError):
    """L'utilisateur n'a pas le rôle requis pour cette action."""


class DuplicateEntityError(SmartExamError):
    """Tentative de création d'une entité déjà existante (unicité)."""
class WrongPasswordError(SmartExamError):
    """Le mot de passe fourni ne correspond pas au hash stocké."""

# --- Erreurs spécifiques au domaine ---

class UserNotFoundError(NotFoundError):
    pass


class InvalidCredentialsError(SmartExamError):
    pass


class ClasseNotFoundError(NotFoundError):
    pass


class MatiereNotFoundError(NotFoundError):
    pass


class ExamenNotFoundError(NotFoundError):
    pass


class ExamResourcesIncompleteError(SmartExamError):
    """Les ressources fournies par le professeur sont insuffisantes
    pour lancer la correction (consignes, corrigé, tests, etc.)."""


class CopieNotFoundError(NotFoundError):
    pass


class CopieAlreadyProcessingError(SmartExamError):
    """Une correction est déjà en cours ou terminée pour cette copie."""


class ResultatNotFoundError(NotFoundError):
    pass


class CorrectionPipelineError(SmartExamError):
    """Erreur remontée par le pipeline IA (ai_pipeline.orchestrator),
    encapsulée pour ne pas exposer directement OrchestratorError
    au reste du backend."""

    def __init__(self, message: str, step: str = "", cause: Exception | None = None):
        self.step = step
        self.cause = cause
        super().__init__(message)
