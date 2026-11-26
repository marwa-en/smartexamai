"""Point d'entrée principal"""
import os
import re
import json
import shutil
from typing import List, Dict, Any
from orchestrator import PipelineOrchestrator

DOSSIER_TEMP = "data/_temp_pipeline"

def demander_fichier(titre: str, description: str) -> str:
    """Demande un chemin de fichier."""
    print(f"\n{'='*70}")
    print(f"📂 {titre}")
    print(f"   {description}")
    print(f"{'='*70}")
    
    while True:
        chemin = input("\n➡️  Chemin du fichier (ou 'q' pour quitter) : ").strip()
        
        if chemin.lower() == 'q':
            print("❌ Annulation.")
            exit(0)
        
        chemin = chemin.strip('"').strip("'")
        
        if not os.path.exists(chemin):
            print(f"❌ Fichier introuvable : {chemin}")
            continue
        
        if not os.path.isfile(chemin):
            print(f"❌ Ce n'est pas un fichier")
            continue
        
        ext = os.path.splitext(chemin)[1].lower()
        if ext not in {".pdf", ".txt", ".md", ".docx"}:
            print(f"❌ Format non supporté : {ext}")
            continue
        
        print(f"✅ {os.path.basename(chemin)}")
        return chemin


def separer_question_reponse(texte: str) -> tuple[str, str]:
    """Sépare question et réponse."""
    texte = texte.strip()
    
    match = re.search(r'\?\s+[A-ZÀ-Ÿ]', texte)
    if match:
        pos = match.start() + 1
        return texte[:pos].strip(), texte[pos+1:].strip()
    
    if '?' in texte:
        pos = texte.index('?')
        return texte[:pos+1].strip(), texte[pos+1:].strip()
    
    if ':' in texte:
        pos = texte.index(':')
        return texte[:pos].strip(), texte[pos+1:].strip()
    
    if '.' in texte:
        pos = texte.index('.')
        return texte[:pos+1].strip(), texte[pos+1:].strip()
    
    return texte, ""


def charger_questions_reponses() -> List[Dict[str, Any]]:
    """Charge les questions/réponses depuis JSON."""
    print(f"\n{'='*70}")
    print(f"📝 FICHIER DES QUESTIONS")
    print(f"{'='*70}")
    
    while True:
        chemin = input("\n➡️  Chemin du fichier JSON : ").strip()
        
        if chemin.lower() == 'q':
            exit(0)
        
        chemin = chemin.strip('"').strip("'")
        
        if not os.path.exists(chemin):
            print(f"❌ Fichier introuvable")
            continue
        
        if not chemin.endswith('.json'):
            print(f"❌ Format JSON requis")
            continue
        
        try:
            with open(chemin, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            questions_list = None
            if isinstance(data, list):
                questions_list = data
            elif isinstance(data, dict):
                if 'extracted_content' in data:
                    questions_list = data['extracted_content']
                elif 'questions' in data:
                    questions_list = data['questions']
                else:
                    print(f"❌ Format non reconnu")
                    continue
            
            questions_formatees = []
            premier = questions_list[0]
            
            if isinstance(premier, dict):
                if 'label' in premier and 'value' in premier:
                    for i, item in enumerate(questions_list):
                        question, reponse = separer_question_reponse(item['value'])
                        if reponse:
                            questions_formatees.append({
                                "label": item['label'],
                                "question": question,
                                "reponse": reponse,
                            })
                elif 'question' in premier and 'reponse' in premier:
                    for i, item in enumerate(questions_list):
                        questions_formatees.append({
                            "label": item.get('label', f"question_{i+1}"),
                            "question": item['question'],
                            "reponse": item['reponse'],
                        })
            
            if not questions_formatees:
                print(f"❌ Aucune question valide")
                continue
            
            print(f"\n✅ {len(questions_formatees)} question(s)")
            return questions_formatees
        
        except Exception as e:
            print(f"❌ Erreur : {e}")
            continue


def nettoyer_dossiers_temporaires():
    """Supprime les dossiers temporaires."""
    if os.path.exists(DOSSIER_TEMP):
        shutil.rmtree(DOSSIER_TEMP)
        print(f"✅ Dossiers temporaires supprimés")


if __name__ == "__main__":
    print("\n" + "🎓 SMARTexamAI".center(70, "="))
    
    try:
        # Demander les fichiers
        chemin_cours = demander_fichier("COURS", "Support de cours")
        chemin_corrige = demander_fichier("CORRIGÉ", "Correction officielle")
        chemin_bareme = demander_fichier("BARÈME", "Grille de notation")
        chemin_consignes = demander_fichier("CONSIGNES", "Instructions")
        
        # Charger les questions
        questions = charger_questions_reponses()
        
        # Fichier de sortie
        fichier_sortie = input("\n➡️  Nom du fichier de sortie (défaut: resultats.json) : ").strip()
        if not fichier_sortie:
            fichier_sortie = "resultats.json"
        if not fichier_sortie.endswith('.json'):
            fichier_sortie += '.json'
        
        # Exécuter le pipeline
        resultat = PipelineOrchestrator.executer(
            chemin_cours=chemin_cours,
            chemin_corrige=chemin_corrige,
            chemin_bareme=chemin_bareme,
            chemin_consignes=chemin_consignes,
            questions=questions,
            fichier_sortie=fichier_sortie,
        )
        
        print("\n" + "✅ TERMINÉ !".center(70, "="))
        print(f"📊 Note : {resultat['synthese']['note_finale']} / {resultat['synthese']['total_points_max']}")
        if resultat['synthese']['note_sur_20']:
            print(f"📊 Sur 20 : {resultat['synthese']['note_sur_20']}/20")
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Interruption")
        nettoyer_dossiers_temporaires()
    except Exception as e:
        print(f"\n❌ Erreur : {e}")
        nettoyer_dossiers_temporaires()
        raise
    finally:
        nettoyer_dossiers_temporaires()