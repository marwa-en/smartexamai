
"""LLM Client for SmartExamAI Grading Module using OpenRouter — SÉCURISÉ."""
from __future__ import annotations

import json
import logging
import os
from typing import Optional

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

# Import du module de sécurité
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from security.llm_guard import extract_json_object, log_llm_call

load_dotenv()

logger = logging.getLogger("smartexamai.llm_client")

# Nombre de tentatives si le JSON est invalide
MAX_RETRIES = 2


class LLMClient:
    """Wrapper autour de ChatOpenAI (LangChain) pointé sur OpenRouter — sécurisé."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = (
            api_key
            or os.environ.get("OPENROUTER_KEY")
            or os.environ.get("OPENROUTER_API_KEY")
            or os.environ.get("API_KEY")
        )
        self.api_base = os.environ.get("OPENAI_API_BASE") or "https://openrouter.ai/api/v1"
        self.model = model or os.environ.get("OPENROUTER_MODEL") or "qwen/qwen3-14b"

        if not self.api_key:
            raise ValueError(
                "Aucune clé API trouvée (API_KEY, OPENROUTER_KEY ou OPENROUTER_API_KEY) "
                "dans le fichier .env"
            )

        self.llm = ChatOpenAI(
            model=self.model,
            temperature=0.2,
            openai_api_key=self.api_key,
            openai_api_base=self.api_base,
            default_headers={
                "HTTP-Referer": "https://smartexamai.local",
                "X-Title": "SmartExamAI",
            } if "openrouter" in self.api_base.lower() else None,
        )

    def grade_submission(self, prompt: str, section: str = "code") -> dict:
        """Envoie le prompt de notation au LLM et retourne le JSON parsé.

        Avec retry automatique si le JSON est invalide.
        """
        messages = [{"role": "user", "content": prompt}]
        last_error: Optional[Exception] = None

        for attempt in range(MAX_RETRIES + 1):
            try:
                response = self.llm.invoke(messages)
                content = response.content
            except Exception as e:
                log_llm_call(
                    section=section,
                    injection_flags=[],
                    output_valid=False,
                    error=str(e),
                )
                raise RuntimeError(
                    f"Échec de l'appel au LLM (OpenRouter, modèle '{self.model}'): {e}"
                ) from e

            try:
                result = extract_json_object(content)

                log_llm_call(
                    section=section,
                    injection_flags=[],
                    output_valid=True,
                    raw_score=result.get("score"),
                )

                return result

            except (json.JSONDecodeError, ValueError) as e:
                last_error = e
                logger.warning(
                    "Tentative %d/%d : JSON invalide du LLM. Erreur: %s",
                    attempt + 1,
                    MAX_RETRIES + 1,
                    e,
                )

                if attempt < MAX_RETRIES:
                    # Ajouter un message de correction pour le prochain essai
                    messages.extend([
                        {"role": "assistant", "content": content},
                        {
                            "role": "user",
                            "content": (
                                "Your previous response was not valid JSON. "
                                "Please respond ONLY with a valid JSON object, "
                                "no markdown, no explanations before or after."
                            ),
                        },
                    ])

        log_llm_call(
            section=section,
            injection_flags=[],
            output_valid=False,
            error=f"JSON invalide après {MAX_RETRIES + 1} tentatives",
        )

        raise ValueError(
            f"Le LLM a renvoyé un JSON invalide après {MAX_RETRIES + 1} tentatives. "
            f"Dernière erreur: {last_error}"
        )