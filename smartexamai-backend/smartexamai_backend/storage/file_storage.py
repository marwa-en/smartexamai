"""
SmartExamAI — Gestion du stockage des fichiers sur disque.

Toutes les copies scannées et ressources d'examen (consignes, corrigés,
tests unitaires, barèmes...) sont organisées sous `settings.storage_root` :

storage_root/
└── examens/
    └── {examen_id}/
        ├── ressources/
        │   ├── consignes.txt
        │   ├── corrige.txt
        │   └── ...
        └── copies/
            └── {copie_id}/
                ├── page_01.png
                └── ...

Ce module ne connaît rien du pipeline IA : il fournit uniquement des
chemins absolus (Path) utilisables ensuite par integration/orchestrator_adapter.py.
"""
from __future__ import annotations

import shutil
import uuid
from pathlib import Path
from typing import Iterable

from configss.settings import settings


def _examen_dir(examen_id: int) -> Path:
    d = settings.storage_root / "examens" / str(examen_id)
    d.mkdir(parents=True, exist_ok=True)
    return d


def ressources_dir(examen_id: int) -> Path:
    d = _examen_dir(examen_id) / "ressources"
    d.mkdir(parents=True, exist_ok=True)
    return d


def copies_dir(examen_id: int) -> Path:
    d = _examen_dir(examen_id) / "copies"
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_resource_file(examen_id: int, source_path: str | Path, target_filename: str) -> Path:
    """Copie un fichier fourni par le professeur/admin vers le stockage
    de l'examen et retourne le chemin absolu final."""
    source = Path(source_path)
    if not source.is_file():
        raise FileNotFoundError(f"Fichier source introuvable : {source}")

    destination = ressources_dir(examen_id) / target_filename
    shutil.copyfile(source, destination)
    return destination.resolve()


def create_copie_folder(examen_id: int, copie_id: int | None = None) -> Path:
    """Crée (et retourne) le dossier destiné à recevoir les images scannées
    d'une copie d'étudiant. Utilise un identifiant temporaire si copie_id
    n'est pas encore connu (avant insertion en base)."""
    identifier = str(copie_id) if copie_id is not None else uuid.uuid4().hex[:12]
    d = copies_dir(examen_id) / identifier
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_copie_images(destination_dir: Path, image_paths: Iterable[str | Path]) -> list[Path]:
    """Copie une liste d'images scannées (pages de la copie) dans destination_dir."""
    saved: list[Path] = []
    for i, img in enumerate(sorted(str(p) for p in image_paths), start=1):
        src = Path(img)
        if not src.is_file():
            raise FileNotFoundError(f"Image introuvable : {src}")
        dst = destination_dir / f"page_{i:02d}{src.suffix.lower()}"
        shutil.copyfile(src, dst)
        saved.append(dst.resolve())
    return saved


def write_students_csv(examen_id: int, csv_content: str) -> Path:
    """Génère le fichier CSV des étudiants d'une classe (students_csv_path
    attendu par OrchestratorConfig) à partir du contenu déjà formaté."""
    path = ressources_dir(examen_id) / "students.csv"
    path.write_text(csv_content, encoding="utf-8")
    return path.resolve()
