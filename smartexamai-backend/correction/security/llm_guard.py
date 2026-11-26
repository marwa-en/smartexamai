"""
SmartExamAI — Module de sécurité pour les appels LLM.

Protège contre :
- Prompt injection indirecte (texte étudiant manipulant le LLM)
- Sorties LLM non conformes
- Scores aberrants
"""
from __future__ import annotations

import json
import logging
import math
import re
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger("smartexamai.llm_guard")


# ============================================================================
# Détection de prompt injection
# ============================================================================

INJECTION_PATTERNS = [
    # Anglais
    r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions?",
    r"disregard\s+(all\s+)?(previous|prior|above)",
    r"forget\s+(all\s+)?(previous|prior|above)",
    r"you\s+are\s+now",
    r"new\s+instructions?",
    r"system\s+prompt",
    r"act\s+as\s+if",
    r"pretend\s+(you\s+are|to\s+be)",
    r"from\s+now\s+on",
    # Français
    r"ignore[rz]?\s+(toutes?\s+)?(les?\s+)?(consignes?|instructions?)\s+(pr[ée]c[ée]dentes?|ci-?dessus)",
    r"oublie[rz]?\s+(toutes?\s+)?(les?\s+)?(consignes?|instructions?)",
    r"tu\s+es\s+maintenant",
    r"nouvelles?\s+(consignes?|instructions?)",
    r"agis?\s+comme\s+si",
    # Tentatives de manipulation de note
    r"(attribue[rz]?|donne[rz]?|mets?|assign)\s+(la\s+)?(note|score)\s+(maximale?|20|100)",
    r"(note|score)\s*[:=]\s*(20|100|maximum)",
    r"perfect\s+score",
    r"full\s+marks?",
    r"give\s+(me\s+)?(a\s+)?(20|100|perfect|full)",
    # Synonymes / reformulations (F-06)
    r"(override|bypass|supersede|replace|cancel)\s+(the\s+)?(earlier|prior|previous|above|system)\s+(guidance|instructions?|rules|prompt)",
    r"mark\s+(this|the)\s+(answer|response|code|copy)\s+as\s+(flawless|perfect|correct|full|excellent)",
    r"print\s+your\s+system\s+prompt",
    r"^\s*#{2,}\s*(system|assistant|developer)\b",
    r"^\s*(system|assistant|developer)\s*:",
    # Espagnol
    r"ignora\s+(todas?\s+)?(las?\s+)?instrucciones\s+(anteriores|previas)",
    r"olvida\s+(todas?\s+)?(las?\s+)?instrucciones",
    r"(pon|da|asigna)\s+(la\s+)?(nota|puntuaci[oó]n)\s+(m[aá]xima|20|100)",
    # Arabe
    r"تجاهل\s+(جميع\s+|كل\s+)?التعليمات",
    r"(الدرجة|العلامة)\s+الكاملة",
]

# Compiler les patterns une seule fois
_COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in INJECTION_PATTERNS]


_HOMOGLYPHS = str.maketrans({
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "у": "y", "х": "x", "і": "i", "ј": "j", "ѕ": "s",
    "ո": "n", "ν": "v", "ο": "o", "α": "a", "ε": "e", "ι": "i", "κ": "k", "ρ": "p", "τ": "t", "υ": "u",
})
_LEET = str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a", "$": "s"})
_B64_RE = re.compile(r"[A-Za-z0-9+/]{20,}={0,2}")


def normalize_for_detection(text: str) -> str:
    """Neutralise les astuces d'évasion : Unicode (NFKC), caractères invisibles, homoglyphes,
    lettres espacées (« i g n o r e »)."""
    import unicodedata
    t = unicodedata.normalize("NFKC", text)
    t = "".join(ch for ch in t if unicodedata.category(ch) != "Cf")      # zero-width, bidi, etc.
    t = t.translate(_HOMOGLYPHS).lower()
    # « i g n o r e   a l l » -> « ignore all » (séquences de ≥4 lettres isolées)
    # (≥ 2 espaces = frontière de mot ; un seul espace entre lettres isolées = lettres d'un même mot)
    segments = re.split(r"\s{2,}", t)
    segments = [re.sub(r"(?<!\S)((?:\w ){2,}\w)(?!\S)", lambda m: m.group(1).replace(" ", ""), seg) for seg in segments]
    return " ".join(segments)


def _decoded_base64_segments(text: str) -> list[str]:
    import base64, binascii
    out = []
    for seg in _B64_RE.findall(text)[:20]:
        try:
            out.append(base64.b64decode(seg + "=" * (-len(seg) % 4), validate=True).decode("utf-8", "ignore"))
        except (binascii.Error, ValueError):
            continue
    return out


def detect_prompt_injection(text: str, _depth: int = 0) -> list[str]:
    """Détecte des tentatives de prompt injection dans un texte.

    Défense en profondeur : cette heuristique ne remplace PAS l'isolation du prompt,
    le bornage du score ni la revue humaine (les attaques par reformulation restent possibles).

    Returns:
        Liste des patterns suspects détectés (vide si aucun).
    """
    if not text:
        return []

    variants = {text, normalize_for_detection(text)}
    variants.add(normalize_for_detection(text).translate(_LEET))
    matches: list[str] = []
    for v in variants:
        for pattern in _COMPILED_PATTERNS:
            if pattern.pattern not in matches and pattern.search(v):
                matches.append(pattern.pattern)

    if _depth == 0 and not matches:        # charges utiles encodées en base64
        for decoded in _decoded_base64_segments(text):
            matches += [f"base64:{m}" for m in detect_prompt_injection(decoded, _depth=1)]

    if matches:
        logger.warning(
            "⚠️ Tentative de prompt injection détectée : %d pattern(s) suspect(s)",
            len(matches),
        )

    return matches


def sanitize_llm_text(text: str, max_length: int = 50_000) -> str:
    """Nettoie un texte issu d'un LLM pour stockage/affichage.

    - Supprime les caractères de contrôle (sauf \\n, \\r, \\t)
    - Limite la longueur
    """
    if not text:
        return ""

    # Supprimer les caractères de contrôle dangereux
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)

    # Limiter la longueur
    return cleaned[:max_length]


# ============================================================================
# Extraction robuste du JSON
# ============================================================================

def extract_json_object(raw: str) -> dict[str, Any]:
    """Extrait un objet JSON d'une réponse LLM, même mal formatée.

    Gère :
    - JSON pur
    - Blocs ```json ... ```
    - JSON entouré de texte
    - JSON partiel (extrait le premier objet trouvé)
    """
    if not raw or not raw.strip():
        raise ValueError("Réponse LLM vide")

    raw = raw.strip()

    # 1. Essayer de parser directement
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return data
        raise ValueError(f"Réponse JSON n'est pas un objet : {type(data)}")
    except json.JSONDecodeError:
        pass

    # 2. Retirer les blocs markdown
    if raw.startswith("```"):
        # Enlever ```json au début et ``` à la fin
        cleaned = re.sub(r"^```(?:json)?\s*", "", raw)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip()
        try:
            data = json.loads(cleaned)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

    # 3. Chercher le premier objet JSON valide
    start = raw.find("{")
    end = raw.rfind("}")

    if start != -1 and end > start:
        candidate = raw[start : end + 1]
        try:
            data = json.loads(candidate)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Impossible d'extraire un objet JSON valide de la réponse LLM")


# ============================================================================
# Modèles Pydantic pour validation stricte
# ============================================================================

class LlmGradeResponse(BaseModel):
    """Réponse attendue du LLM pour la notation de code."""

    score: float = Field(..., description="Note attribuée")
    max_score: float = Field(default=20.0, description="Note maximale possible")
    overall_assessment: str = Field(default="", max_length=2000)
    algorithm_correct: bool = Field(default=False)
    syntax_errors: list[str] = Field(default_factory=list)
    logical_errors: list[str] = Field(default_factory=list)
    runtime_errors: list[str] = Field(default_factory=list)
    failed_tests_analysis: list[dict] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    feedback: str = Field(default="", max_length=5000)
    suggested_improvements: list[str] = Field(default_factory=list)

    @field_validator("score", "max_score")
    @classmethod
    def score_must_be_finite(cls, v: float) -> float:
        if not math.isfinite(v):
            raise ValueError("Le score doit être un nombre fini")
        return v

    @field_validator(
        "overall_assessment",
        "feedback",
        mode="before",
    )
    @classmethod
    def sanitize_text_fields(cls, v: str) -> str:
        if not isinstance(v, str):
            return ""
        return sanitize_llm_text(v)

    @field_validator(
        "syntax_errors",
        "logical_errors",
        "runtime_errors",
        "strengths",
        "weaknesses",
        "suggested_improvements",
        mode="before",
    )
    @classmethod
    def sanitize_list_fields(cls, v: list) -> list[str]:
        if not isinstance(v, list):
            return []
        return [sanitize_llm_text(str(item), max_length=1000) for item in v]


class LlmTranscriptionResponse(BaseModel):
    """Réponse attendue du LLM pour la transcription de rédaction."""

    transcription: str = Field(..., max_length=50_000)

    @field_validator("transcription")
    @classmethod
    def clean_transcription(cls, v: str) -> str:
        return sanitize_llm_text(v, max_length=50_000)


# ============================================================================
# Clamp du score
# ============================================================================

def clamp_score(score: float, max_score: float) -> float:
    """Borne un score entre 0 et max_score.

    Ne fait JAMAIS confiance au LLM pour retourner un score valide.
    """
    if not math.isfinite(score):
        logger.warning("Score non fini reçu du LLM, remplacé par 0")
        return 0.0

    if max_score <= 0:
        logger.warning("max_score <= 0, score forcé à 0")
        return 0.0

    if score < 0:
        logger.warning("Score négatif (%.2f) reçu du LLM, clamé à 0", score)
        return 0.0

    if score > max_score:
        logger.warning(
            "Score (%.2f) supérieur au max (%.2f) reçu du LLM, clamé",
            score,
            max_score,
        )
        return float(max_score)

    return float(score)


# ============================================================================
# Logging d'audit
# ============================================================================

def log_llm_call(
    *,
    section: str,
    injection_flags: list[str],
    output_valid: bool,
    raw_score: Optional[float] = None,
    clamped_score: Optional[float] = None,
    error: Optional[str] = None,
) -> None:
    """Journalise un appel LLM pour audit (sans données sensibles)."""
    logger.info(
        "LLM_CALL section=%s injection_flags=%s output_valid=%s "
        "raw_score=%s clamped_score=%s error=%s",
        section,
        ",".join(injection_flags) if injection_flags else "none",
        output_valid,
        raw_score,
        clamped_score,
        error,
    )