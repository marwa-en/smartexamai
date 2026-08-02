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
  
    # ... (attributs existants) ...
    
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

    def ensure_directories(self) -> None:
        self.storage_root.mkdir(parents=True, exist_ok=True)
        self.pipeline_work_root.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_directories()