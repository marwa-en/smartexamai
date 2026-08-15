
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from configss.settings import settings
from core.exceptions import (
    CopieAlreadyProcessingError,
    DuplicateEntityError,
    NotFoundError,
    PermissionDeniedError,
    SmartExamError,
)
from db.init_db import init_db

from app.routers import auth, classes, copies, correction, etudiant, examens, matieres, professeur, users

# --- Validation sécurité au démarrage ---

INSECURE_JWT_SECRETS = {
    "",
    "dev-secret-change-me-in-production",
    "change-me",
    "secret",
}


def validate_security_configuration() -> None:
    """Refuse le démarrage en production avec une configuration dangereuse."""
    if not settings.is_production():
        # En développement, on ne bloque pas, mais on alerte si secret faible.
        if settings.jwt_secret in INSECURE_JWT_SECRETS:
            import logging
            logging.getLogger("smartexamai").warning(
                "⚠️ SMARTEXAM_JWT_SECRET utilise une valeur par défaut non sécurisée. "
                "Ce n'est pas bloquant en développement, mais il faudra un secret fort en production."
            )
        return

    # En production : validations strictes
    if settings.jwt_secret in INSECURE_JWT_SECRETS:
        raise RuntimeError(
            "🔒 Sécurité : SMARTEXAM_JWT_SECRET doit être défini avec une valeur forte "
            "en production. Utilisez un secret aléatoire d'au moins 32 caractères."
        )

    cors_origins = settings.get_cors_origins_list()
    if "*" in cors_origins:
        raise RuntimeError(
            "🔒 Sécurité : SMARTEXAM_CORS_ORIGINS ne doit pas contenir '*' en production. "
            "Définissez explicitement les origines autorisées."
        )

    if not cors_origins:
        raise RuntimeError(
            "🔒 Sécurité : SMARTEXAM_CORS_ORIGINS doit contenir au moins une origine en production."
        )

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Avant démarrage : validation sécurité
    validate_security_configuration()
    
    # Initialisation base de données
    init_db(create_default_admin=True)
    
    yield
    
app = FastAPI(
    title="SmartExamAI API",
    description="API FastAPI pour la plateforme SmartExamAI (correction automatique de copies d'examen).",
     lifespan=lifespan,
)

# --- CORS : autorise le frontend React (Vite en dev, build statique en prod) ---
_default_origins = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000"
_allowed_origins = os.environ.get("SMARTEXAM_CORS_ORIGINS", _default_origins).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Gestion centralisée des exceptions métier ---

@app.exception_handler(NotFoundError)
async def not_found_handler(request: Request, exc: NotFoundError):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(PermissionDeniedError)
async def permission_denied_handler(request: Request, exc: PermissionDeniedError):
    return JSONResponse(status_code=403, content={"detail": str(exc)})


@app.exception_handler(DuplicateEntityError)
async def duplicate_handler(request: Request, exc: DuplicateEntityError):
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(CopieAlreadyProcessingError)
async def already_processing_handler(request: Request, exc: CopieAlreadyProcessingError):
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(SmartExamError)
async def smartexam_error_handler(request: Request, exc: SmartExamError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


# --- Initialisation de la base de données au démarrage ---


@app.get("/api/health", tags=["health"])
def health() -> dict:
    return {"status": "ok"}


# --- Routers ---
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(classes.router)
app.include_router(matieres.router)
app.include_router(examens.router)
app.include_router(copies.router)
app.include_router(correction.router)
app.include_router(professeur.router)
app.include_router(etudiant.router)
