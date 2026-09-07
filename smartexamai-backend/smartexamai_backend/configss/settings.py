"""
SmartExamAI — Configuration centralisée du backend.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# BASE_DIR = dossier smartexamai_backend
BASE_DIR = Path(__file__).resolve().parent.parent

# PROJECT_ROOT = vraie racine du projet (parent de smartexamai_backend)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

@dataclass(frozen=True)
class Settings:
    # --- Base de données ---
    database_url: str = os.environ.get(
        "SMARTEXAM_DATABASE_URL", f"sqlite:///{BASE_DIR / 'smartexamai.db'}"
    )
    echo_sql: bool = os.environ.get("SMARTEXAM_ECHO_SQL", "false").lower() == "true"

    # --- Stockage des fichiers déposés ---
    storage_root: Path = field(
        default_factory=lambda: Path(
            os.environ.get("SMARTEXAM_STORAGE_ROOT", str(BASE_DIR / "storage_data"))
        ).resolve()
    )

    # --- Racine du projet du pipeline IA ---
    # ⚠️ CORRECTION : on utilise PROJECT_ROOT au lieu de BASE_DIR
    pipeline_project_root: Path = field(
        default_factory=lambda: Path(
            os.environ.get("SMARTEXAM_PIPELINE_ROOT", str(PROJECT_ROOT))
        ).resolve()  # .resolve() garantit un chemin absolu (ex: C:\...\fol)
    )

    # --- Dossier de travail temporaire du pipeline ---
    pipeline_work_root: Path = field(
        default_factory=lambda: Path(
            os.environ.get("SMARTEXAM_PIPELINE_WORK_ROOT", str(PROJECT_ROOT / "pipeline_work"))
        ).resolve()
    )

    # --- Clés API ---
    api_key: str | None = os.environ.get("API_KEY")
    openrouter_key: str | None = os.environ.get("OPENROUTER_API_KEY")

    # --- Sécurité ---
        
    password_hash_iterations: int = int(
        os.environ.get("SMARTEXAM_PBKDF2_ITERATIONS", "260000")
    )

    # --- Environnement d'exécution ---
    # Valeurs acceptées : "development", "staging", "production"
    environment: str = os.environ.get("SMARTEXAM_ENVIRONMENT", "development").strip().lower()

    # --- JWT ---
    # Secret utilisé pour signer/valider les tokens Bearer.
    # ⚠️ Doit être une valeur forte en production (voir validate_security_configuration dans main.py).
    jwt_secret: str = os.environ.get(
        "SMARTEXAM_JWT_SECRET", "dev-secret-change-me-in-production"
    )

    # Ancien secret JWT, utilisé uniquement pendant une rotation de secret
    # (pour ne pas invalider brutalement toutes les sessions).
    jwt_previous_secret: str | None = os.environ.get("SMARTEXAM_JWT_PREVIOUS_SECRET")

    # --- Admin bootstrap ---
    # Email utilisé si aucun admin n'existe en base au premier démarrage.
    admin_bootstrap_email: str = os.environ.get(
        "ADMIN_BOOTSTRAP_EMAIL", "admin@localhost"
    ).strip().lower()

    # --- CORS ---
    # Liste blanche des origines autorisées, séparées par des virgules.
    # Exemple : "http://localhost:5173,https://smartexam.example.com"
    cors_origins: str = os.environ.get(
        "SMARTEXAM_CORS_ORIGINS", "http://localhost:5173"
    )

    # ... (attributs existants) ...
  
    # ... (attributs existants) ...
        # --- Durées de vie des tokens ---
    # Access token court (15 min par défaut)
    jwt_access_token_expire_minutes: int = int(
        os.environ.get("SMARTEXAM_ACCESS_TOKEN_MINUTES", "15")
    )
    # Refresh token long (14 jours par défaut)
    refresh_token_expire_days: int = int(
        os.environ.get("SMARTEXAM_REFRESH_TOKEN_DAYS", "14")
    )
    
    # --- Configuration du pipeline de correction code (sandbox Docker) ---
    # Ces valeurs sont utilisées par correction/code/sandbox/
        # --- Configuration du pipeline de correction code (sandbox Docker) ---
    # Utilisés par correction/code/sandbox/{python,c,java,php}_runner.py
    docker_image_python: str = os.environ.get("DOCKER_IMAGE_PYTHON", "python:3.11-slim")
    docker_image_php: str = os.environ.get("DOCKER_IMAGE_PHP", "php:8.2-cli")
    docker_image_java: str = os.environ.get("DOCKER_IMAGE_JAVA", "openjdk:17-slim")
    docker_image_c: str = os.environ.get("DOCKER_IMAGE_C", "gcc:latest")

    docker_timeout: int = int(os.environ.get("DOCKER_TIMEOUT", "10"))
    docker_memory_limit: str = os.environ.get("DOCKER_MEMORY_LIMIT", "256m")
    docker_max_output_size: int = int(os.environ.get("DOCKER_MAX_OUTPUT_SIZE", "1048576"))
        # --- Méthodes utilitaires ---

    def is_production(self) -> bool:
        return self.environment in {"production", "prod"}

    def get_cors_origins_list(self) -> list[str]:
        if not self.cors_origins:
            return []
        return [
            origin.strip()
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]

    def ensure_directories(self) -> None:
        self.storage_root.mkdir(parents=True, exist_ok=True)
        self.pipeline_work_root.mkdir(parents=True, exist_ok=True)
    


settings = Settings()
settings.ensure_directories()