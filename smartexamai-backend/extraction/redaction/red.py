import os
import base64
import json
from mistralai.client import Mistral
from dotenv import load_dotenv
import logging
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from security.llm_guard import detect_prompt_injection, sanitize_llm_text, log_llm_call

logger = logging.getLogger("smartexamai.redaction")
load_dotenv()


SYSTEM_PROMPT = """
Tu es un moteur d'extraction de données visuelles (VLM) de haute précision des reponses a des 
questions de redaction d'un examen d'informatique manuscrites.

RÈGLES D'EXTRACTION STRICTES :
1. Extrais EXACTEMENT et UNIQUEMENT ce qui est visible sur l'image.
2. Si une zone est illisible, raturée ou manquante, retourne la chaîne exacte : "[ILLISIBLE]".
3. Ne ajoute aucun commentaire, aucune introduction, aucune conclusion.

FORMAT DE SORTIE OBLIGATOIRE :
- Tu dois répondre UNIQUEMENT avec un objet JSON valide.
- N'inclus pas de balises markdown (pas de ```json ... ```).
- Structure attendue : 
{
  "metadata": { "matiere": "string", "type_doc": "string" },
  "extracted_content": [
    { "label": "string", "value": "string" }
  ]
}
"""


def build_variable_prompt(matiere: str, type_examen: str, consignes: str, contexte: str) -> str:
    return f"""
    CONTEXTE LÉGER : {contexte}
    MATIÈRE : {matiere}
    TYPE D'EXAMEN : {type_examen}

    CONSIGNES COURTES POUR CETTE IMAGE :
    {consignes}
    """

def encode_image_to_base64(image_path: str) -> str:
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


def process_exam_image(image_path: str, matiere: str, type_examen: str, consignes: str, contexte: str):
    api_key = os.environ.get("API_KEY")
    client = Mistral(api_key=api_key)

    user_text_prompt = build_variable_prompt(matiere, type_examen, consignes, contexte)
    base64_image = encode_image_to_base64(image_path)
    image_url = f"data:image/jpeg;base64,{base64_image}"

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": user_text_prompt},
                {"type": "image_url", "image_url": {"url": image_url}}
            ]
        }
    ]

    response = client.chat.complete(
        model="mistral-medium-latest",
        messages=messages,
        response_format={"type": "json_object"},
        temperature=0.0
    )

    raw_content = response.choices[0].message.content

    if raw_content.startswith("```json"):
        raw_content = raw_content[7:-3]
    elif raw_content.startswith("```"):
        raw_content = raw_content[3:-2]

    try:
        return json.loads(raw_content)
        extracted_text = ""
        if "extracted_content" in result and isinstance(result["extracted_content"], list):
            for item in result["extracted_content"]:
                if isinstance(item, dict) and "value" in item:
                    extracted_text += str(item["value"]) + "\n"

        injection_flags = detect_prompt_injection(extracted_text)

        if injection_flags:
            logger.warning(
                "⚠️ Tentative de prompt injection détectée dans la rédaction : %s",
                injection_flags,
            )
            result["injection_flags"] = injection_flags
            result["requires_human_review"] = True

        log_llm_call(
            section="redaction_extraction",
            injection_flags=injection_flags,
            output_valid=True,
        )

        return result

    except json.JSONDecodeError:
        log_llm_call(
            section="redaction_extraction",
            injection_flags=[],
            output_valid=False,
            error="JSON invalide",
        )
        return None
   


