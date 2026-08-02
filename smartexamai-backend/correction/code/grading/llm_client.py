"""LLM Client for SmartExamAI Grading Module using OpenRouter.

Aligné sur le même style que le module de correction de rédaction
(correction/redaction/services/corrector_service.py) : on utilise
langchain_openai.ChatOpenAI plutôt que des appels HTTP bruts (requests).
C'est ce client, avec cette même résolution de clé/headers, qui fonctionne
de façon fiable avec la configuration OpenRouter du projet.
"""
import os
import json
from typing import Optional

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()


class LLMClient:
    """Wrapper autour de ChatOpenAI (LangChain) pointé sur OpenRouter.

    Même stratégie de résolution de clé API et de configuration que
    CorrectorService.creer_llm() côté rédaction, pour un comportement
    identique entre les deux modules de correction.
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        # Même ordre de priorité que corrector_service.creer_llm()
        self.api_key = (
            api_key
            or os.environ.get("OPENROUTER_KEY")
            or os.environ.get("OPENROUTER_API_KEY")
            or os.environ.get("API_KEY")
        )
        self.api_base = os.environ.get("OPENAI_API_BASE") or "https://openrouter.ai/api/v1"
        # Modèle configurable via l'env (OPENROUTER_MODEL), aligné par défaut
        # sur le modèle qui fonctionne déjà côté rédaction.
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

    @staticmethod
    def _parser_json(texte: str) -> dict:
        """Extrait le JSON de la réponse du LLM (retire un éventuel bloc ```json ... ```).

        Identique à CorrectorService.parser_json côté rédaction.
        """
        texte_clean = texte.strip()
        if texte_clean.startswith("```"):
            lignes = texte_clean.split("\n")
            debut, fin = 0, len(lignes)
            for i, ligne in enumerate(lignes):
                if ligne.strip().startswith("```"):
                    if debut == 0:
                        debut = i + 1
                    else:
                        fin = i
                        break
            texte_clean = "\n".join(lignes[debut:fin])
        return json.loads(texte_clean)

    def grade_submission(self, prompt: str) -> dict:
        """Envoie le prompt de notation au LLM et retourne le JSON parsé."""
        try:
            response = self.llm.invoke(prompt)
            content = response.content
        except Exception as e:
            raise RuntimeError(
                f"Échec de l'appel au LLM (OpenRouter, modèle '{self.model}'): {e}"
            ) from e

        try:
            return self._parser_json(content)
        except json.JSONDecodeError:
            raise ValueError(f"Le LLM a renvoyé un JSON invalide. Contenu brut: {content}")
