"""Service de correction RAG"""
import json
from typing import List, Dict, Any
from langchain_core.documents import Document
from langchain_openai import ChatOpenAI


NOM_MODELE_LLM = "qwen/qwen3-14b"
TEMPERATURE = 0.3

class CorrectorService:
    """Service responsable de la correction via RAG."""
    
    @staticmethod
    def creer_llm() -> ChatOpenAI:
        """Crée le LLM via OpenRouter ou une clé compatible."""
        import os
        # Priorité aux variables LangChain standards ou à la clé API_KEY du .env
        api_key = os.environ.get("OPENROUTER_KEY") or os.environ.get("OPENROUTER_API_KEY") or os.environ.get("API_KEY")
        api_base = os.environ.get("OPENAI_API_BASE") or "https://openrouter.ai/api/v1"
        
        if not api_key:
            raise ValueError("Aucune clé API trouvée (API_KEY, OPENROUTER_KEY ou OPENROUTER_API_KEY) dans le fichier .env")
        
        # Si on utilise le proxy Manus en interne (pour les tests de Manus)
        if "manus" in api_base.lower() or os.environ.get("OPENAI_API_KEY") == api_key:
            model_name = "gpt-4o"
        else:
            model_name = NOM_MODELE_LLM # Utilise le modèle configuré dans settings.py (ex: qwen)
            
        return ChatOpenAI(
            model=model_name,
            temperature=TEMPERATURE,
            openai_api_key=api_key,
            openai_api_base=api_base,
            default_headers={
                "HTTP-Referer": "https://github.com/smartexamai",
                "X-Title": "SmartExamAI",
            } if "openrouter" in api_base.lower() else None
        )
    
    @staticmethod
    def formater_contexte(docs: List[Document]) -> str:
        """Formate les documents récupérés."""
        texte = ""
        for i, doc in enumerate(docs, 1):
            cat = doc.metadata.get("categorie", "?").upper()
            source = doc.metadata.get("source", "?")
            texte += f"\n[Source {i} - {cat} - {source}]\n{doc.page_content}\n"
        return texte
    
    @staticmethod
    def construire_prompt(question: str, reponse: str, contexte: str,
                         bareme: str, corrige_officiel: str, consignes: str) -> str:
        """Construit le prompt pour le LLM."""
        return f"""You are an experienced university professor.

Votre tâche : évaluer la réponse d'un étudiant.

Règles :
    - Évaluez UNIQUEMENT selon la solution officielle fournie.
    - Respectez strictement le barème et les consignes de correction.
    - Accordez des points partiels lorsque c'est approprié.
    - Expliquez brièvement et de manière constructive la note attribuée.
    - Retournez UNIQUEMENT du JSON valide dans le format exact spécifié.
    Récapitulatif des consignes générales pour le correcteur
Élément	Tolérance / Pénalité
Oubli d’un critère mineur (ex. pas d’exemple)	Retirer 0,5 pt maximum
Confusion technique grave 	Retirer 1 à 2 pts selon la gravité
Réponse trop vague 	Ne pas donner plus de la moitié des points
Réponse structurée, claire, avec exemples	Attribuer le maximum
Vocabulaire simplifié mais correct	Accepter sans pénalité
Absence de distinction entre les deux parties (ex. Q5)	Retirer 1 pt
ce n est pas grave si l etudiant ne respecte pas l'ordre ou commet des erreur d orthographe ou de vocabulaire tolere
 tout ca et ne diminue pas de notes si juste tu sens
 de la reponse que l etudiant comprend le contexte donne la note complete 
meme si quelques points sont manquants tolere jusqu a 3 points
 manquants et donne la note complete
Format JSON à retourner :
{{
  "score": nombre_attribue,
  "score_max": nombre_total_possible,
  "feedback": "explication constructive",
  "points_cles_valide": ["liste"],
  "points_manquants": ["liste"]
}}

CONSIGNES :
{consignes}

CONTEXTE :
{contexte}

QUESTION :
{question}

BARÈME :
{bareme}

CORRIGÉ OFFICIEL :
{corrige_officiel}

RÉPONSE ÉTUDIANT :
{reponse}

Retournez UNIQUEMENT le JSON."""
    
    @staticmethod
    def parser_json(texte: str) -> Dict[str, Any]:
        """Parse le JSON retourné par le LLM."""
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
    
    @staticmethod
    def corriger_question(llm: ChatOpenAI, retriever, question: str, reponse: str,
                         bareme: str, corrige_officiel: str, consignes: str) -> Dict[str, Any]:
        """Corrige une question via RAG."""
        docs = retriever.invoke(question)
        contexte = CorrectorService.formater_contexte(docs)
        prompt = CorrectorService.construire_prompt(
            question, reponse, contexte, bareme, corrige_officiel, consignes
        )
        
        try:
            response = llm.invoke(prompt)
            resultat = CorrectorService.parser_json(response.content)
            resultat["statut"] = "succes"
            return resultat
        except Exception as e:
            return {
                "statut": "erreur",
                "erreur": str(e),
            }