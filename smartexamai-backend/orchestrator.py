"""
SmartExamAI — Orchestrateur global du pipeline d'examen.

Enchaîne automatiquement : Segmentation → Prétraitement → Extraction → Correction.
Réutilise les modules existants sans les modifier.

Usage :
    config = OrchestratorConfig(
        images_dir=Path("scans"),
        consignes_path=Path("consignes.txt"),
        corrige_path=Path("corrige.txt"),
        unit_tests_path=Path("tests.json"),
        code_consignes_path=Path("consignes_code.txt"), # <--- NOUVEAU
        ...
    )
    result = SmartExamOrchestrator(config).run()
"""
from __future__ import annotations

import dataclasses
import importlib.util
import json
import logging
import os
import re
import sys
import time
import traceback
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Sequence, Type

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class OrchestratorError(Exception):
    """Erreur de base de l'orchestrateur."""

    def __init__(self, message: str, step: str = "", section: str = "", cause: Optional[BaseException] = None):
        self.step = step
        self.section = section
        self.cause = cause
        detail = message
        if step:
            detail = f"[{step}] {detail}"
        if section:
            detail = f"{detail} (section={section})"
        if cause:
            detail = f"{detail} — cause: {cause}"
        super().__init__(detail)


class ConfigurationError(OrchestratorError):
    pass


class SegmentationError(OrchestratorError):
    pass


class PreprocessingError(OrchestratorError):
    pass


class ExtractionError(OrchestratorError):
    pass


class CorrectionError(OrchestratorError):
    pass


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

class Section(str, Enum):
    INFO = "info"
    QCM = "qcm"
    REDACTION = "redaction"
    CODE = "code"


@dataclass
class RedactionMetadata:
    matiere: str = "Informatique"
    type_examen: str = "Examen"
    contexte: str = ""


@dataclass
class CodeExerciseMetadata:
    language: str = "python"
    exercise_type: str = "function"  # "function" | "program"
    title: str = "Exercice de programmation"
    function_name: Optional[str] = None
    rubric: Dict[str, Any] = field(default_factory=lambda: {"total": 20})
    subject: str = "Informatique"
    exam_type: str = "Examen"


@dataclass
class OrchestratorConfig:
    """Configuration centralisée — aucun chemin codé en dur."""

    images_dir: Path
    consignes_path: Path
    corrige_path: Path
    unit_tests_path: Path
    
    # <--- NOUVEAU : Consignes spécifiques à l'exercice de code
    code_consignes_path: Optional[Path] = None

    project_root: Optional[Path] = None
    work_dir: Optional[Path] = None

    students_csv_path: Optional[Path] = None
    qcm_template_path: Optional[Path] = None
    qcm_answer_key_path: Optional[Path] = None
    cours_path: Optional[Path] = None
    bareme_path: Optional[Path] = None

    sections: Sequence[Section] = field(
        default_factory=lambda: [Section.INFO, Section.QCM, Section.REDACTION, Section.CODE]
    )
    redaction_metadata: RedactionMetadata = field(default_factory=RedactionMetadata)
    code_exercise: CodeExerciseMetadata = field(default_factory=CodeExerciseMetadata)

    scoring_system: str = "normal"  # "normal" | "canadian"
    api_key: Optional[str] = None
    openrouter_key: Optional[str] = None

    log_level: str = "INFO"
    log_file: Optional[Path] = None
    show_progress: bool = True
    cleanup_work_dir: bool = False

    def __post_init__(self) -> None:
        self.images_dir = Path(self.images_dir)
        self.consignes_path = Path(self.consignes_path)
        self.corrige_path = Path(self.corrige_path)
        self.unit_tests_path = Path(self.unit_tests_path)
        
        # <--- NOUVEAU : Conversion en Path
        if self.code_consignes_path is not None:
            self.code_consignes_path = Path(self.code_consignes_path)

        if self.project_root is None:
            self.project_root = Path(__file__).resolve().parent.parent
        else:
            self.project_root = Path(self.project_root)

        if self.work_dir is None:
            ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            self.work_dir = self.project_root / "orchestrator" / "work" / ts
        else:
            self.work_dir = Path(self.work_dir)

        for attr in (
            "students_csv_path", "qcm_template_path", "qcm_answer_key_path",
            "cours_path", "bareme_path", "log_file",
        ):
            val = getattr(self, attr)
            if val is not None:
                setattr(self, attr, Path(val))


# ---------------------------------------------------------------------------
# Résultat final
# ---------------------------------------------------------------------------

@dataclass
class FinalResult:
    """Résultat final de correction — seule sortie publique du pipeline."""

    student: Optional[Dict[str, Any]] = None
    qcm: Optional[Dict[str, Any]] = None
    redaction: Optional[Dict[str, Any]] = None
    code: Optional[Dict[str, Any]] = None
    summary: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Utilitaires internes
# ---------------------------------------------------------------------------

def _import_module_from_path(module_name: str, file_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Impossible de charger le module depuis {file_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _ensure_sys_path(directory: Path) -> None:
    path_str = str(directory.resolve())
    if path_str not in sys.path:
        sys.path.insert(0, path_str)


@contextmanager
def _working_directory(path: Path) -> Iterator[None]:
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def _separer_question_reponse(texte: str) -> tuple[str, str]:
    texte = texte.strip()
    match = re.search(r"\?\s+[A-ZÀ-Ÿ]", texte)
    if match:
        pos = match.start() + 1
        return texte[:pos].strip(), texte[pos + 1 :].strip()
    if "?" in texte:
        pos = texte.index("?")
        return texte[: pos + 1].strip(), texte[pos + 1 :].strip()
    if ":" in texte:
        pos = texte.index(":")
        return texte[:pos].strip(), texte[pos + 1 :].strip()
    if "." in texte:
        pos = texte.index(".")
        return texte[: pos + 1].strip(), texte[pos + 1 :].strip()
    return texte, ""


def _formater_questions_redaction(extraction: Dict[str, Any]) -> List[Dict[str, Any]]:
    raw_items = extraction.get("extracted_content") or extraction.get("questions") or []
    if not isinstance(raw_items, list):
        raise ExtractionError("Format d'extraction rédaction invalide", step="extraction", section="redaction")

    questions: List[Dict[str, Any]] = []
    for i, item in enumerate(raw_items):
        if not isinstance(item, dict):
            continue
        if "question" in item and "reponse" in item:
            questions.append({
                "label": item.get("label", f"question_{i + 1}"),
                "question": item["question"],
                "reponse": item["reponse"],
            })
        elif "value" in item:
            question, reponse = _separer_question_reponse(str(item["value"]))
            if reponse:
                questions.append({
                    "label": item.get("label", f"question_{i + 1}"),
                    "question": question,
                    "reponse": reponse,
                })
    if not questions:
        raise ExtractionError("Aucune question/réponse exploitable", step="extraction", section="redaction")
    return questions


def _exam_report_to_dict(report: Any) -> Dict[str, Any]:
    if dataclasses.is_dataclass(report):
        return dataclasses.asdict(report)
    if hasattr(report, "__dict__"):
        return dict(report.__dict__)
    return {"value": report}


def _grading_result_to_dict(result: Any) -> Dict[str, Any]:
    if hasattr(result, "model_dump"):
        return result.model_dump()
    if hasattr(result, "dict"):
        return result.dict()
    if dataclasses.is_dataclass(result):
        return dataclasses.asdict(result)
    return {"value": result}


class _ProgressTracker:
    """Barre de progression (tqdm si disponible, sinon logs)."""

    PHASES = ("segmentation", "preprocessing", "extraction", "correction")

    def __init__(self, enabled: bool, logger: logging.Logger, total_units: int = 4):
        self.enabled = enabled
        self.logger = logger
        self.total_units = max(total_units, 1)
        self._current = 0
        self._bar = None

        if enabled:
            try:
                from tqdm import tqdm  # type: ignore
                self._bar = tqdm(total=self.total_units, desc="Pipeline", unit="phase")
            except ImportError:
                self.logger.info("tqdm non installé — progression via logs uniquement")

    def advance(self, phase: str, message: str = "") -> None:
        self._current += 1
        label = message or phase
        if self._bar is not None:
            self._bar.set_description(f"{phase}")
            self._bar.update(1)
        pct = round(100 * self._current / self.total_units, 1)
        self.logger.info("Progression %s%% — %s", pct, label)

    def close(self) -> None:
        if self._bar is not None:
            self._bar.close()


# ---------------------------------------------------------------------------
# Orchestrateur principal
# ---------------------------------------------------------------------------

class SmartExamOrchestrator:
    """Orchestre le pipeline complet SmartExamAI."""

    PREPROCESS_SECTIONS = (Section.REDACTION, Section.CODE)

    def __init__(self, config: OrchestratorConfig):
        self.config = config
        self.logger = self._setup_logging()
        self._modules: Dict[str, Any] = {}
        self._segments_dir = self.config.work_dir / "segments"
        self._preprocessed_dir = self.config.work_dir / "preprocessed"
        self._extraction_dir = self.config.work_dir / "extraction"
        self._correction_dir = self.config.work_dir / "correction"

    # ------------------------------------------------------------------
    # API publique
    # ------------------------------------------------------------------

    def validate_config(self) -> None:
        """Valide la configuration avant exécution."""
        required = [
            ("images_dir", self.config.images_dir, "dossier"),
            ("consignes_path", self.config.consignes_path, "fichier"),
            ("corrige_path", self.config.corrige_path, "fichier"),
            ("unit_tests_path", self.config.unit_tests_path, "fichier"),
        ]
        for name, path, kind in required:
            if kind == "dossier" and not path.is_dir():
                raise ConfigurationError(f"{name} introuvable ou invalide : {path}")
            if kind == "fichier" and not path.is_file():
                raise ConfigurationError(f"{name} introuvable : {path}")

        images = list(self._list_images(self.config.images_dir))
        if not images:
            raise ConfigurationError(f"Aucune image dans {self.config.images_dir}")

        section_requirements = {
            Section.INFO: [("students_csv_path", self.config.students_csv_path)],
            Section.QCM: [
                ("qcm_template_path", self.config.qcm_template_path),
                ("qcm_answer_key_path", self.config.qcm_answer_key_path),
            ],
            Section.REDACTION: [],
            Section.CODE: [
                ("code_consignes_path", self.config.code_consignes_path) # <--- NOUVEAU
            ],
        }
        for section in self.config.sections:
            for attr, value in section_requirements.get(section, []):
                if value is None or (isinstance(value, Path) and not value.is_file()):
                    raise ConfigurationError(
                        f"Section '{section.value}' activée mais '{attr}' manquant ou invalide"
                    )

        if Section.CODE in self.config.sections:
            try:
                with open(self.config.unit_tests_path, encoding="utf-8") as f:
                    tests = json.load(f)
                if not isinstance(tests, list) or not tests:
                    raise ConfigurationError("unit_tests_path doit contenir une liste non vide")
            except json.JSONDecodeError as exc:
                raise ConfigurationError(f"unit_tests_path JSON invalide : {exc}") from exc

    def run(self) -> FinalResult:
        """Exécute le pipeline et retourne uniquement le résultat final."""
        started = time.perf_counter()
        self.validate_config()
        self._prepare_work_dirs()
        self._bootstrap_imports()

        progress = _ProgressTracker(
            enabled=self.config.show_progress,
            logger=self.logger,
            total_units=4,
        )

        segments: Dict[str, Path] = {}
        preprocessed: Dict[str, Path] = {}
        extraction: Dict[str, Any] = {}
        correction: Dict[str, Any] = {}

        try:
            # 1. Segmentation
            self.logger.info("=== Phase 1/4 : Segmentation ===")
            segments = self._run_segmentation()
            progress.advance("segmentation", f"{len(segments)} segment(s) produit(s)")

            # 2. Prétraitement
            self.logger.info("=== Phase 2/4 : Prétraitement ===")
            preprocessed = self._run_preprocessing(segments)
            progress.advance("preprocessing", f"{len(preprocessed)} image(s) traitée(s)")

            # 3. Extraction
            self.logger.info("=== Phase 3/4 : Extraction ===")
            extraction = self._run_extraction(segments, preprocessed)
            progress.advance("extraction", f"{len(extraction)} section(s) extraite(s)")

            # 4. Correction
            self.logger.info("=== Phase 4/4 : Correction ===")
            correction = self._run_correction(extraction)
            progress.advance("correction", "correction terminée")

            elapsed = round(time.perf_counter() - started, 2)
            final = self._build_final_result(correction, elapsed)
            self.logger.info("Pipeline terminé en %ss", elapsed)
            return final

        except OrchestratorError:
            raise
        except Exception as exc:
            self.logger.error("Erreur inattendue : %s\n%s", exc, traceback.format_exc())
            raise OrchestratorError("Échec du pipeline", step="run", cause=exc) from exc
        finally:
            progress.close()
            if self.config.cleanup_work_dir and self.config.work_dir:
                self._cleanup_work_dir()

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def _setup_logging(self) -> logging.Logger:
        logger = logging.getLogger("smartexam.orchestrator")
        logger.handlers.clear()
        logger.setLevel(getattr(logging, self.config.log_level.upper(), logging.INFO))
        formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")

        console = logging.StreamHandler(sys.stdout)
        console.setFormatter(formatter)
        logger.addHandler(console)

        if self.config.log_file:
            self.config.log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(self.config.log_file, encoding="utf-8")
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        return logger

    def _prepare_work_dirs(self) -> None:
        for directory in (
            self.config.work_dir,
            self._segments_dir,
            self._preprocessed_dir,
            self._extraction_dir,
            self._correction_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)
        self.logger.debug("Répertoire de travail : %s", self.config.work_dir)

    def _cleanup_work_dir(self) -> None:
        import shutil
        if self.config.work_dir and self.config.work_dir.exists():
            shutil.rmtree(self.config.work_dir, ignore_errors=True)
            self.logger.debug("work_dir supprimé : %s", self.config.work_dir)

    def _bootstrap_imports(self) -> None:
        root = self.config.project_root
        
        _ensure_sys_path(root)
        _ensure_sys_path(root / "correction")
        _ensure_sys_path(root / "correction" / "redaction")
        _ensure_sys_path(root / "correction" / "code")
        _ensure_sys_path(root / "extraction")

        module_map = {
            "segmentation": root / "segmentatio" / "segmentation.py",
            "preprocess": root / "pretraitement" / "preprocess.py",
            "student_info": root / "extraction" / "info" / "student.py",
            "qcm_extract": root / "extraction" / "qcm" / "qcm.py",
            "redaction_extract": root / "extraction" / "redaction" / "red.py",
            "code_extract": root / "extraction" / "code" / "code.py",
            "qcm_correct": root / "correction" / "qcm" / "corr_qcm.py",
            "redaction_pipeline": root / "correction" / "redaction" / "orchestrator.py",
        }
        
        for name, path in module_map.items():
            if not path.is_file():
                raise ConfigurationError(f"Module requis introuvable : {path}")
            self._modules[name] = _import_module_from_path(f"smartexam_{name}", path)

    @staticmethod
    def _list_images(directory: Path) -> List[Path]:
        extensions = {".png", ".jpg", ".jpeg"}
        return sorted(p for p in directory.iterdir() if p.suffix.lower() in extensions)

    def _segment_path(self, section: Section, preprocessed: Dict[str, Path], segments: Dict[str, Path]) -> Path:
        key = section.value
        if key in preprocessed:
            return preprocessed[key]
        if key in segments:
            return segments[key]
        raise ExtractionError(f"Segment '{key}' introuvable", step="extraction", section=key)

    def _write_placeholder(self, name: str, content: str = "") -> Path:
        path = self.config.work_dir / name
        path.write_text(content, encoding="utf-8")
        return path

    # ------------------------------------------------------------------
    # Phase 1 — Segmentation
    # ------------------------------------------------------------------

    def _run_segmentation(self) -> Dict[str, Path]:
        try:
            segment_images = self._modules["segmentation"].segment_images
            segment_images(str(self.config.images_dir), str(self._segments_dir))
        except Exception as exc:
            raise SegmentationError("Échec de la segmentation", step="segmentation", cause=exc) from exc

        segments: Dict[str, Path] = {}
        for section in self.config.sections:
            candidate = self._segments_dir / f"{section.value}.png"
            if candidate.is_file():
                segments[section.value] = candidate
            else:
                self.logger.warning("Segment absent (ignoré) : %s", candidate.name)

        if not segments:
            raise SegmentationError("Aucun segment produit", step="segmentation")
        return segments

    # ------------------------------------------------------------------
    # Phase 2 — Prétraitement
    # ------------------------------------------------------------------

    def _run_preprocessing(self, segments: Dict[str, Path]) -> Dict[str, Path]:
        preprocess = self._modules["preprocess"].preprocess_handwritten_exam
        preprocessed: Dict[str, Path] = {}

        for section in self.config.sections:
            if section not in self.PREPROCESS_SECTIONS:
                continue
            key = section.value
            if key not in segments:
                self.logger.warning("Prétraitement ignoré — segment '%s' absent", key)
                continue
            src = segments[key]
            dst = self._preprocessed_dir / f"{key}.png"
            try:
                preprocess(str(src), str(dst))
                if dst.is_file():
                    preprocessed[key] = dst
                    self.logger.info("Prétraitement OK : %s", key)
                else:
                    self.logger.warning("Prétraitement sans sortie pour %s — image source conservée", key)
                    preprocessed[key] = src
            except Exception as exc:
                raise PreprocessingError(
                    f"Échec du prétraitement pour '{key}'",
                    step="preprocessing",
                    section=key,
                    cause=exc,
                ) from exc
        return preprocessed

    # ------------------------------------------------------------------
    # Phase 3 — Extraction
    # ------------------------------------------------------------------

    def _run_extraction(
        self,
        segments: Dict[str, Path],
        preprocessed: Dict[str, Path],
    ) -> Dict[str, Any]:
        results: Dict[str, Any] = {}

        if Section.INFO in self.config.sections:
            results["info"] = self._extract_info(segments)

        if Section.QCM in self.config.sections:
            results["qcm"] = self._extract_qcm(segments)

        if Section.REDACTION in self.config.sections:
            results["redaction"] = self._extract_redaction(segments, preprocessed)

        if Section.CODE in self.config.sections:
            results["code"] = self._extract_code(segments, preprocessed)

        if not results:
            raise ExtractionError("Aucune extraction réalisée", step="extraction")
        return results

    def _extract_info(self, segments: Dict[str, Path]) -> Dict[str, Any]:
        if "info" not in segments:
            raise ExtractionError("Segment info.png absent", step="extraction", section="info")
        try:
            student_mod = self._modules["student_info"]
            student_mod.CSV_PATH = str(self.config.students_csv_path)
            student_mod.IMAGE_PATH = str(segments["info"])

            from mistralai.client import Mistral  # import différé

            api_key = self.config.api_key or os.environ.get("API_KEY")
            if not api_key:
                raise ExtractionError("API_KEY manquante pour l'extraction info", step="extraction", section="info")

            collection = student_mod.setup_rag()
            client = Mistral(api_key=api_key)
            validation = student_mod.process_image(client, collection)
            student = validation.get("selected_student") if isinstance(validation, dict) else None
            return {"student": student}
        except OrchestratorError:
            raise
        except Exception as exc:
            raise ExtractionError("Échec extraction info", step="extraction", section="info", cause=exc) from exc

    def _extract_qcm(self, segments: Dict[str, Path]) -> Dict[str, Any]:
        if "qcm" not in segments:
            raise ExtractionError("Segment qcm.png absent", step="extraction", section="qcm")
        try:
            process_qcm = self._modules["qcm_extract"].process_qcm
            answers = process_qcm(str(segments["qcm"]), str(self.config.qcm_template_path))
            serializable = {str(k): v for k, v in answers.items()}
            out_path = self._extraction_dir / "qcm.json"
            out_path.write_text(json.dumps(serializable, ensure_ascii=False, indent=2), encoding="utf-8")
            return {"answers": serializable, "file_path": str(out_path)}
        except OrchestratorError:
            raise
        except Exception as exc:
            raise ExtractionError("Échec extraction QCM", step="extraction", section="qcm", cause=exc) from exc

    def _extract_redaction(
        self,
        segments: Dict[str, Path],
        preprocessed: Dict[str, Path],
    ) -> Dict[str, Any]:
        if Section.REDACTION not in self.config.sections:
            return {}
        try:
            image_path = self._segment_path(Section.REDACTION, preprocessed, segments)
            consignes_text = self.config.consignes_path.read_text(encoding="utf-8")
            meta = self.config.redaction_metadata
            process_exam_image = self._modules["redaction_extract"].process_exam_image
            result = process_exam_image(
                str(image_path),
                meta.matiere,
                meta.type_examen,
                consignes_text,
                meta.contexte,
            )
            if result is None:
                raise ExtractionError("Extraction rédaction nulle (JSON invalide)", step="extraction", section="redaction")
            out_path = self._extraction_dir / "redaction.json"
            out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            return {"data": result, "file_path": str(out_path)}
        except OrchestratorError:
            raise
        except Exception as exc:
            raise ExtractionError("Échec extraction rédaction", step="extraction", section="redaction", cause=exc) from exc

    def _extract_code(
        self,
        segments: Dict[str, Path],
        preprocessed: Dict[str, Path],
    ) -> Dict[str, Any]:
        if "code" not in segments:
            raise ExtractionError("Segment code.png absent", step="extraction", section="code")
        try:
            image_path = self._segment_path(Section.CODE, preprocessed, segments)
            extract_code = self._modules["code_extract"].extract_code
            meta = self.config.code_exercise
            teacher_input = {
                "language": meta.language,
                "subject": meta.subject,
                "exam_type": meta.exam_type,
            }
            code_dir = self._extraction_dir / "code"
            code_dir.mkdir(parents=True, exist_ok=True)
            with _working_directory(code_dir):
                result = extract_code(
                    str(image_path),
                    teacher_input,
                    api_key=self.config.api_key,
                )
            
            code_text = result.get("code", "") if isinstance(result, dict) else str(result)
            self._visualize_extracted_code(code_text, meta.language)
            
            return result
        except OrchestratorError:
            raise
        except Exception as exc:
            raise ExtractionError("Échec extraction code", step="extraction", section="code", cause=exc) from exc

    def _visualize_extracted_code(self, code_text: str, language: str) -> None:
        """Affiche le code extrait dans la console de manière lisible et le sauvegarde."""
        print("\n" + "🔍 " + "VISUALISATION DU CODE EXTRAIT".center(64) + " 🔍")
        print(f"{'=' * 70}")
        print(f"📌 Langage : {language.upper()}")
        print(f"{'-' * 70}")
        
        if not code_text or not code_text.strip():
            print("⚠️  Aucun code n'a été extrait ou le code est vide.")
        else:
            lines = code_text.split('\n')
            for i, line in enumerate(lines, 1):
                formatted_line = line.replace('\t', '    ')
                print(f"{i:4d} │ {formatted_line}")
        
        print(f"{'=' * 70}\n")
        
        if self._extraction_dir:
            safe_lang = re.sub(r'[^a-zA-Z0-9]', '', language).lower() or 'txt'
            code_file = self._extraction_dir / f"code_extrait.{safe_lang}"
            try:
                code_file.write_text(code_text, encoding="utf-8")
                self.logger.info("💾 Code extrait sauvegardé dans : %s", code_file.resolve())
            except Exception as e:
                self.logger.warning("Impossible de sauvegarder le code extrait : %s", e)
    

    # ------------------------------------------------------------------
    # Phase 4 — Correction
    # ------------------------------------------------------------------

    def _run_correction(self, extraction: Dict[str, Any]) -> Dict[str, Any]:
        results: Dict[str, Any] = {}

        if Section.INFO in self.config.sections and "info" in extraction:
            results["student"] = extraction["info"].get("student")

        if Section.QCM in self.config.sections and "qcm" in extraction:
            results["qcm"] = self._correct_qcm(extraction["qcm"])

        if Section.REDACTION in self.config.sections and "redaction" in extraction:
            results["redaction"] = self._correct_redaction(extraction["redaction"]["data"])

        if Section.CODE in self.config.sections and "code" in extraction:
            results["code"] = self._correct_code(extraction["code"])

        return results

    def _correct_qcm(self, qcm_extraction: Dict[str, Any]) -> Dict[str, Any]:
        try:
            corr_mod = self._modules["qcm_correct"]
            detected_path = self._correction_dir / "qcm_detected.json"
            detected_path.write_text(
                json.dumps(qcm_extraction["answers"], ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            report = corr_mod.correct_exam(
                str(detected_path),
                str(self.config.qcm_answer_key_path),
                self.config.scoring_system,
            )
            out_path = self._correction_dir / "qcm_result.json"
            corr_mod.save_report_to_json(report, str(out_path))
            return _exam_report_to_dict(report)
        except Exception as exc:
            raise CorrectionError("Échec correction QCM", step="correction", section="qcm", cause=exc) from exc

    def _correct_redaction(self, extraction_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            questions = _formater_questions_redaction(extraction_data)
            cours = self.config.cours_path or self._write_placeholder("cours_placeholder.txt")
            bareme = self.config.bareme_path or self._write_placeholder("bareme_placeholder.txt", "Barème non fourni")
            output_file = self._correction_dir / "redaction_result.json"

            pipeline = self._modules["redaction_pipeline"].PipelineOrchestrator
            return pipeline.executer(
                chemin_cours=str(cours),
                chemin_corrige=str(self.config.corrige_path),
                chemin_bareme=str(bareme),
                chemin_consignes=str(self.config.consignes_path),
                questions=questions,
                fichier_sortie=str(output_file),
            )
        except OrchestratorError:
            raise
        except Exception as exc:
            raise CorrectionError("Échec correction rédaction", step="correction", section="redaction", cause=exc) from exc

    def _correct_code(self, code_extraction: Dict[str, Any]) -> Dict[str, Any]:
      try:
        from models.exercise import Exercise, ExerciseType, TestCase
        from preprocessing.cleaner import CodeCleaner
        from preprocessing.language_detector import LanguageDetector
        from preprocessing.validator import SubmissionValidator
        from preprocessing.syntax_repair import repair_code
        from sandbox.python_runner import PythonRunner
        from sandbox.c_runner import CRunner
        from sandbox.java_runner import JavaRunner
        from sandbox.php_runner import PhpRunner
        from grading.grader import CodeGrader
        
        student_code = code_extraction.get("code", "")
        meta = self.config.code_exercise

        with open(self.config.unit_tests_path, encoding="utf-8") as f:
            raw_tests = json.load(f)
        test_cases = [
            TestCase(input_data=str(t["input"]), expected_output=str(t["expected"]))
            for t in raw_tests
        ]

        exercise_type = ExerciseType.FUNCTION if meta.exercise_type.lower() == "function" else ExerciseType.PROGRAM
        
        consignes_file = self.config.code_consignes_path or self.config.consignes_path
        consignes_text = consignes_file.read_text(encoding="utf-8")
        
        reference_solution = self.config.corrige_path.read_text(encoding="utf-8")

        exercise = Exercise(
            title=meta.title,
            statement=consignes_text,
            language=meta.language.lower(),
            type=exercise_type,
            rubric=meta.rubric,
            test_cases=test_cases,
            reference_solution=reference_solution,
            function_name=meta.function_name,
            consignes=consignes_text,
        )

        cleaned = CodeCleaner().clean(student_code)
        language = LanguageDetector().detect(cleaned, hint=meta.language)
        valid, error = SubmissionValidator().validate(cleaned, language)
        if not valid:
            raise CorrectionError(f"Code étudiant invalide : {error}", step="correction", section="code")

        runners: Dict[str, Type] = {
            "python": PythonRunner,
            "c": CRunner,
            "java": JavaRunner,
            "php": PhpRunner,
        }
        runner_cls = runners.get(language)
        if runner_cls is None:
            raise CorrectionError(
                f"Langage non supporté par le sandbox : {language}",
                step="correction",
                section="code",
            )

        runner = runner_cls()
        execution_report = runner.run(cleaned, exercise, exercise.test_cases)
        api_key = self.config.openrouter_key or self.config.api_key
        grader = CodeGrader(api_key=api_key)
        
        # ✅ AJOUT 1 : Récupérer les flags d'injection AVANT la notation
        injection_flags = code_extraction.get("injection_flags", [])
        requires_review = code_extraction.get("requires_human_review", False)

        if requires_review:
            self.logger.warning(
                "⚠️ Code extrait avec suspicion de prompt injection. "
                "Flags: %s. La copie sera marquée pour revue humaine.",
                injection_flags,
            )
        
        # Notation par le LLM
        grading = grader.grade(exercise, cleaned, execution_report, language, cleaned)
        grading_result = _grading_result_to_dict(grading)

        # ✅ AJOUT 2 : Propager les flags d'injection dans le résultat final
        grading_result["injection_flags"] = injection_flags
        grading_result["requires_human_review"] = requires_review

        return grading_result

      except OrchestratorError:
        raise
      except Exception as exc:
        raise CorrectionError("Échec correction code", step="correction", section="code", cause=exc) from exc
    # ------------------------------------------------------------------
    # Résultat final
    # ------------------------------------------------------------------

    def _build_final_result(self, correction: Dict[str, Any], elapsed_seconds: float) -> FinalResult:
        summary = self._build_summary(correction)
        metadata = {
            "date": datetime.now(timezone.utc).isoformat(),
            "elapsed_seconds": elapsed_seconds,
            "sections_processed": [s.value for s in self.config.sections],
            "work_dir": str(self.config.work_dir),
        }
        return FinalResult(
            student=correction.get("student"),
            qcm=correction.get("qcm"),
            redaction=correction.get("redaction"),
            code=correction.get("code"),
            summary=summary,
            metadata=metadata,
        )

    def _build_summary(self, correction: Dict[str, Any]) -> Dict[str, Any]:
        sections_corrected: List[str] = []
        scores: List[float] = []
        max_scores: List[float] = []

        qcm = correction.get("qcm")
        if qcm:
            sections_corrected.append("qcm")
            scores.append(float(qcm.get("raw_score", 0)))
            max_scores.append(float(qcm.get("max_possible_score", 0)))

        redaction = correction.get("redaction")
        if redaction and isinstance(redaction, dict):
            synthese = redaction.get("synthese") or {}
            if synthese.get("note_finale") is not None:
                sections_corrected.append("redaction")
                scores.append(float(synthese.get("total_points_obtenus", 0)))
                max_scores.append(float(synthese.get("total_points_max", 0)))

        code = correction.get("code")
        if code:
            sections_corrected.append("code")
            scores.append(float(code.get("score", 0)))
            max_scores.append(float(code.get("max_score", 0)))

        total_score = round(sum(scores), 2) if scores else None
        total_max = round(sum(max_scores), 2) if max_scores else None
        percentage = round(100 * total_score / total_max, 2) if total_score is not None and total_max else None

        return {
            "sections_corrected": sections_corrected,
            "total_score": total_score,
            "max_score": total_max,
            "percentage": percentage,
        }


# ---------------------------------------------------------------------------
# Saisie interactive (CLI)
# ---------------------------------------------------------------------------

def _demander_chemin(
    titre: str,
    description: str,
    *,
    kind: str = "file",
    extensions: Optional[set[str]] = None,
    obligatoire: bool = True,
) -> Optional[Path]:
    """Demande un chemin fichier ou dossier, un par un."""
    print(f"\n{'=' * 70}")
    print(f"📂 {titre}")
    print(f"   {description}")
    if not obligatoire:
        print("   (Entrée vide pour ignorer)")
    print(f"{'=' * 70}")

    while True:
        prompt = "\n➡️  Chemin" + (" (ou 'q' pour quitter)" if obligatoire else " (ou Entrée pour ignorer, 'q' pour quitter)") + " : "
        chemin = input(prompt).strip()

        if chemin.lower() == "q":
            print("❌ Annulation.")
            raise SystemExit(0)

        if not chemin:
            if obligatoire:
                print("❌ Ce chemin est obligatoire.")
                continue
            return None

        chemin = chemin.strip('"').strip("'")
        path = Path(chemin)

        if not path.exists():
            print(f"❌ Introuvable : {path}")
            continue

        if kind == "dir" and not path.is_dir():
            print("❌ Ce n'est pas un dossier.")
            continue

        if kind == "file" and not path.is_file():
            print("❌ Ce n'est pas un fichier.")
            continue

        if kind == "file" and extensions:
            ext = path.suffix.lower()
            if ext not in extensions:
                print(f"❌ Format non supporté : {ext} (attendu : {', '.join(sorted(extensions))})")
                continue

        label = path.name if kind == "file" else str(path)
        print(f"✅ {label}")
        return path.resolve()


def _demander_oui_non(question: str, defaut: bool = False) -> bool:
    """Pose une question oui/non."""
    suffix = "O/n" if defaut else "o/N"
    while True:
        reponse = input(f"\n➡️  {question} ({suffix}) : ").strip().lower()
        if not reponse:
            return defaut
        if reponse in {"o", "oui", "y", "yes"}:
            return True
        if reponse in {"n", "non", "no"}:
            return False
        print("❌ Répondez par o (oui) ou n (non).")


def _demander_langage() -> str:
    """Demande le langage de l'exercice code."""
    langages = {"1": "python", "2": "c", "3": "java", "4": "php"}
    print(f"\n{'=' * 70}")
    print("💻 LANGAGE DE L'EXERCICE CODE")
    print("   1. Python   2. C   3. Java   4. PHP")
    print(f"{'=' * 70}")
    while True:
        choix = input("\n➡️  Votre choix (défaut : 1) : ").strip() or "1"
        if choix in langages:
            lang = langages[choix]
            print(f"✅ {lang}")
            return lang
        if choix.lower() in langages.values():
            print(f"✅ {choix.lower()}")
            return choix.lower()
        print("❌ Choix invalide.")


def _demander_scoring_qcm() -> str:
    """Demande le système de notation QCM."""
    print(f"\n{'=' * 70}")
    print("📊 SYSTÈME DE NOTATION QCM")
    print("   1. Normal (+1 bonne réponse, 0 sinon)")
    print("   2. Canadien (+1 bonne, -1 mauvaise)")
    print(f"{'=' * 70}")
    while True:
        choix = input("\n➡️  Votre choix (défaut : 1) : ").strip() or "1"
        if choix == "1":
            return "normal"
        if choix == "2":
            return "canadian"
        print("❌ Choix invalide (1 ou 2).")


def _construire_config_interactive() -> OrchestratorConfig:
    """Guide l'utilisateur pour saisir tous les chemins un par un."""
    print("\n" + "🎓 SMARTexamAI — Orchestrateur".center(70, "="))
    print("\nSaisissez les chemins un par un.\n")

    images_dir = _demander_chemin(
        "IMAGES",
        "Dossier contenant les pages scannées de l'examen (PNG, JPG)",
        kind="dir",
    )
    consignes_path = _demander_chemin(
        "CONSIGNES GÉNÉRALES",
        "Fichier des consignes générales de l'examen",
        extensions={".txt", ".md", ".pdf", ".docx"},
    )
    corrige_path = _demander_chemin(
        "CORRIGÉ",
        "Fichier du corrigé officiel",
        extensions={".txt", ".md", ".pdf", ".docx", ".json", ".py", ".php", ".c", ".java"},
    )
    unit_tests_path = _demander_chemin(
        "TESTS UNITAIRES",
        "Fichier JSON des cas de test (exercice code)",
        extensions={".json"},
    )
    
    # <--- NOUVEAU : Demande des consignes spécifiques au code
    code_consignes_path = _demander_chemin(
        "CONSIGNES DE CODE",
        "Fichier détaillant les contraintes, signatures de fonctions et règles de l'exercice de code",
        extensions={".txt", ".md", ".pdf", ".docx", ".py", ".java", ".c", ".php"},
    )

    cours_path = _demander_chemin(
        "COURS (optionnel)",
        "Support de cours pour la correction rédaction (RAG)",
        extensions={".txt", ".md", ".pdf", ".docx"},
        obligatoire=False,
    )
    bareme_path = _demander_chemin(
        "BARÈME (optionnel)",
        "Grille de notation pour la rédaction",
        extensions={".txt", ".md", ".pdf", ".docx"},
        obligatoire=False,
    )

    activer_qcm = _demander_oui_non("Corriger la section QCM ?", defaut=True)
    qcm_template_path = None
    qcm_answer_key_path = None
    scoring_system = "normal"
    if activer_qcm:
        qcm_template_path = _demander_chemin(
            "TEMPLATE QCM",
            "Image template pour l'alignement des bulles QCM",
            extensions={".png", ".jpg", ".jpeg"},
        )
        qcm_answer_key_path = _demander_chemin(
            "CORRIGÉ QCM",
            "Fichier JSON du corrigé QCM",
            extensions={".json"},
        )
        scoring_system = _demander_scoring_qcm()

    activer_info = _demander_oui_non("Identifier l'étudiant (section info) ?", defaut=True)
    students_csv_path = None
    if activer_info:
        students_csv_path = _demander_chemin(
            "LISTE ÉTUDIANTS",
            "Fichier CSV officiel des étudiants (nom, prénom, cne, classe, matiere)",
            extensions={".csv"},
        )

    language = _demander_langage()

    sections = [Section.REDACTION, Section.CODE]
    if activer_qcm:
        sections.insert(0, Section.QCM)
    if activer_info:
        sections.insert(0, Section.INFO)

    print(f"\n{'=' * 70}")
    print("📋 RÉCAPITULATIF")
    print(f"   Images           : {images_dir}")
    print(f"   Consignes gén.   : {consignes_path}")
    print(f"   Consignes code   : {code_consignes_path}") # <--- NOUVEAU
    print(f"   Corrigé          : {corrige_path}")
    print(f"   Tests            : {unit_tests_path}")
    print(f"   Sections         : {', '.join(s.value for s in sections)}")
    print(f"   Langage          : {language}")
    print(f"{'=' * 70}")

    if not _demander_oui_non("Lancer le pipeline ?", defaut=True):
        print("❌ Annulation.")
        raise SystemExit(0)

    return OrchestratorConfig(
        images_dir=images_dir,
        consignes_path=consignes_path,
        corrige_path=corrige_path,
        unit_tests_path=unit_tests_path,
        code_consignes_path=code_consignes_path, # <--- NOUVEAU
        cours_path=cours_path,
        bareme_path=bareme_path,
        qcm_template_path=qcm_template_path,
        qcm_answer_key_path=qcm_answer_key_path,
        students_csv_path=students_csv_path,
        sections=sections,
        scoring_system=scoring_system,
        code_exercise=CodeExerciseMetadata(language=language),
        show_progress=True,
    )


# ---------------------------------------------------------------------------
# Point d'entrée
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    try:
        cfg = _construire_config_interactive()
        orchestrator = SmartExamOrchestrator(cfg)
        final = orchestrator.run()

        print("\n" + "✅ TERMINÉ".center(70, "="))
        if final.summary.get("total_score") is not None:
            print(
                f"📊 Score global : {final.summary['total_score']} / "
                f"{final.summary['max_score']} ({final.summary.get('percentage')}%)"
            )
        print("\n--- Résultat final ---\n")
        print(json.dumps(dataclasses.asdict(final), ensure_ascii=False, indent=2))

    except KeyboardInterrupt:
        print("\n\n⚠️  Interruption.")
        raise SystemExit(1)
    except OrchestratorError as exc:
        print(f"\n❌ Erreur : {exc}")
        raise SystemExit(1)