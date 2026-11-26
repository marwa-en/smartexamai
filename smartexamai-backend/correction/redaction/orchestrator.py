"""Orchestrateur du pipeline"""
import os
import json
from datetime import datetime
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor
from services.loader_service import LoaderService
from services.cleaner_service import CleanerService
from services.chunker_service import ChunkerService
from services.vectorizer_service import VectorizerService
from services.corrector_service import CorrectorService

DOSSIER_TEMP = "data/_temp_pipeline"
NB_CHUNKS_RECHERCHE = 3

# Nombre de questions corrigées en parallèle. Chaque appel LLM (une par
# question) est indépendant des autres (recherche RAG + appel HTTP au
# modèle), donc les paralléliser réduit fortement le temps total dès qu'il
# y a plus d'une question. On garde une limite raisonnable pour rester
# gentil avec le rate-limit de l'API.
MAX_CORRECTIONS_PARALLELES = 5


class PipelineOrchestrator:
    """Orchestre l'exécution du pipeline complet."""
    
    @staticmethod
    def executer(chemin_cours: str, chemin_corrige: str, chemin_bareme: str,
                chemin_consignes: str, questions: List[Dict[str, Any]],
                fichier_sortie: str) -> Dict[str, Any]:
        """Exécute le pipeline complet."""
        print("\n" + "🎓 SMARTexamAI - Pipeline".center(70, "="))

        # Empreinte des fichiers de référence, calculée AVANT tout chargement.
        # Optimisation : "cours.pdf" (le plus gros fichier, souvent plusieurs
        # Mo) est identique d'une copie à l'autre pour un même examen. S'il
        # n'a pas changé depuis la dernière correction, on évite complètement
        # de le re-parser/chunker/ré-embedder (l'étape la plus coûteuse du
        # pipeline) et on réutilise directement le vectorstore déjà calculé.
        source_hash = VectorizerService.calculer_empreinte_sources(
            [chemin_cours, chemin_corrige, chemin_bareme, chemin_consignes]
        )
        embeddings = VectorizerService.creer_modele_embedding()
        reutiliser_vectorstore = VectorizerService.vectorstore_en_cache(source_hash)

        # 1. Chargement + nettoyage
        print("\n📂 [1/5] Chargement et nettoyage...")
        fichiers_sources = {
            "corrige": chemin_corrige,
            "bareme": chemin_bareme,
            "consignes": chemin_consignes,
        }
        if not reutiliser_vectorstore:
            # On ne recharge le cours (gros fichier) que si nécessaire.
            fichiers_sources = {"cours": chemin_cours, **fichiers_sources}
        else:
            print("   ♻️  COURS : vectorstore déjà à jour, chargement ignoré")

        tous_docs_nettoyes = []
        textes_complets = {"bareme": "", "corrige": "", "consignes": ""}
        
        for categorie, chemin in fichiers_sources.items():
            docs = LoaderService.charger_fichier(chemin, categorie)
            docs_nettoyes = CleanerService.nettoyer_et_sauvegarder(docs, categorie)
            tous_docs_nettoyes.extend(docs_nettoyes)
            
            if categorie in textes_complets:
                textes_complets[categorie] = " ".join(d.page_content for d in docs_nettoyes)
            
            print(f"   ✅ {categorie.upper()} : {len(docs_nettoyes)} page(s)")
        
        # 2. Chunking
        print("\n🔪 [2/5] Chunking...")
        chunks = ChunkerService.chunker_documents(tous_docs_nettoyes) if not reutiliser_vectorstore else []
        print(f"   ✅ {len(chunks)} chunk(s)" if not reutiliser_vectorstore else "   ♻️  Chunking ignoré (vectorstore réutilisé)")
        
        # 3. Vectorisation
        print("\n🧠 [3/5] Vector Store...")
        vectorstore = VectorizerService.creer_vectorstore(chunks, embeddings, source_hash=source_hash)
        retriever = vectorstore.as_retriever(
            search_type="similarity",
            search_kwargs={"k": NB_CHUNKS_RECHERCHE},
        )
        print(f"   ✅ {vectorstore.index.ntotal} vecteurs")
        
        # 4. Correction
        # Optimisation : chaque question est corrigée indépendamment
        # (recherche RAG + un appel LLM), donc on les traite en parallèle
        # plutôt qu'en boucle séquentielle.
        print("\n🎓 [4/5] Correction RAG...")
        llm = CorrectorService.creer_llm()

        def _corriger(i_q):
            i, q = i_q
            label = q.get("label", f"question_{i}")
            question = q["question"]
            reponse = q["reponse"]
            print(f"\n   📝 {label} : {question[:60]}...")

            resultat = CorrectorService.corriger_question(
                llm=llm,
                retriever=retriever,
                question=question,
                reponse=reponse,
                bareme=textes_complets["bareme"],
                corrige_officiel=textes_complets["corrige"],
                consignes=textes_complets["consignes"],
            )

            resultat["label"] = label
            resultat["numero_question"] = i
            resultat["question"] = question
            resultat["reponse_etudiant"] = reponse
            return i, resultat

        items = list(enumerate(questions, 1))
        resultats_par_index = {}
        nb_threads = max(1, min(MAX_CORRECTIONS_PARALLELES, len(items)))
        with ThreadPoolExecutor(max_workers=nb_threads) as executor:
            for i, resultat in executor.map(_corriger, items):
                resultats_par_index[i] = resultat

        resultats_questions = [resultats_par_index[i] for i, _ in items]

        total_points_obtenus = 0.0
        total_points_max = 0.0
        for resultat in resultats_questions:
            if resultat.get("statut") == "succes":
                try:
                    total_points_obtenus += float(resultat.get("score", 0))
                    total_points_max += float(resultat.get("score_max", 0))
                except (TypeError, ValueError):
                    pass
        
        # 5. Résultat final
        note_finale = round(total_points_obtenus, 2) if total_points_max > 0 else None
        note_sur_20 = round((total_points_obtenus / total_points_max) * 20, 2) if total_points_max > 0 else None
        
        sortie = {
            "metadata": {
                "date_correction": datetime.now().isoformat(),
                "nb_questions": len(questions),
                "nb_chunks": len(chunks) if chunks else vectorstore.index.ntotal,
            },
            "synthese": {
                "total_points_obtenus": round(total_points_obtenus, 2),
                "total_points_max": round(total_points_max, 2),
                "note_finale": note_finale,
                "note_sur_20": note_sur_20,
                "pourcentage": round((total_points_obtenus / total_points_max) * 100, 2) if total_points_max > 0 else None,
            },
            "questions": resultats_questions,
        }
        
        with open(fichier_sortie, "w", encoding="utf-8") as f:
            json.dump(sortie, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 [5/5] Résultats : {fichier_sortie}")
        return sortie