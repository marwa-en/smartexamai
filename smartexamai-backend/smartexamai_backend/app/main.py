"""
SmartExamAI — Application FastAPI.

Expose, via une API REST/JSON, l'ensemble des fonctionnalités jusque-là
disponibles uniquement via cli.py : gestion des utilisateurs/classes/
matières/examens (admin), dépôt et correction automatique des copies,
définition des ressources et consultation des résultats (professeur),
consultation des notes (étudiant).

Lancement (depuis le dossier smartexamai_backend) :
    uvicorn app.main:app --reload --port 8000
"""
from __future__ import annotations

import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from core.exceptions import (
    CopieAlreadyProcessingError,
    DuplicateEntityError,
    NotFoundError,
    PermissionDeniedError,
    SmartExamError,
)
from db.init_db import init_db

from app.routers import auth, classes, copies, correction, etudiant, examens, matieres, professeur, users

app = FastAPI(
    title="SmartExamAI API",
    description="API FastAPI pour la plateforme SmartExamAI (correction automatique de copies d'examen).",
    version="1.0.0",
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

@app.on_event("startup")
def on_startup() -> None:
    init_db(create_default_admin=True)


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
