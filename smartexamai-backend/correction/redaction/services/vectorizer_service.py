"""Service de vectorisation et création du Vector Store"""
import os
import hashlib
from typing import List, Optional
from langchain_core.documents import Document
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
DOSSIER_TEMP = "data/_temp_pipeline"
DOSSIER_VECTORSTORE = os.path.join(DOSSIER_TEMP, "vectorstore")
# Modèles
MODELE_EMBEDDING = "sentence-transformers/all-MiniLM-L6-v2"
# --- Caches process-local -------------------------------------------------
# Optimisation : le modèle d'embedding (HuggingFace, chargé depuis le disque)
# et le vectorstore FAISS (construit à partir de cours.pdf, qui peut faire
# plusieurs Mo) sont recréés à chaque correction dans la version d'origine.
# C'est le principal poste de temps du pipeline de correction rédaction :
# ~tout le cours est ré-embeddé à chaque copie corrigée, alors que les
# fichiers de référence (cours/corrigé/barème/consignes) ne changent
# généralement pas entre deux copies d'un même examen.
#
# On garde donc :
#   - une instance unique du modèle d'embedding en mémoire (process),
#   - le dernier vectorstore construit, associé à une empreinte des
#     fichiers sources ; s'ils n'ont pas changé, on réutilise le
#     vectorstore déjà en mémoire ou sauvegardé sur disque au lieu de
#     tout recalculer.
_EMBEDDINGS_CACHE: Optional[HuggingFaceEmbeddings] = None
_VECTORSTORE_CACHE = {"source_hash": None, "vectorstore": None}

_INDEX_DIR = os.path.join(DOSSIER_VECTORSTORE, "faiss_index")
_HASH_FILE = os.path.join(DOSSIER_VECTORSTORE, "source.hash")


class VectorizerService:
    """Service responsable de la vectorisation."""

    @staticmethod
    def creer_modele_embedding() -> HuggingFaceEmbeddings:
        """Charge le modèle d'embedding (une seule fois par process)."""
        global _EMBEDDINGS_CACHE
        if _EMBEDDINGS_CACHE is None:
            _EMBEDDINGS_CACHE = HuggingFaceEmbeddings(
                model_name=MODELE_EMBEDDING,
                model_kwargs={'device': 'cpu'},
                encode_kwargs={'normalize_embeddings': True}
            )
        return _EMBEDDINGS_CACHE

    @staticmethod
    def calculer_empreinte_sources(chemins: List[str]) -> str:
        """Calcule une empreinte (hash) à partir du contenu des fichiers
        sources (cours/corrigé/barème/consignes). Si l'empreinte n'a pas
        changé depuis la dernière correction, on peut réutiliser le
        vectorstore déjà calculé au lieu de tout re-vectoriser."""
        hasher = hashlib.sha256()
        for chemin in sorted(c for c in chemins if c):
            try:
                with open(chemin, "rb") as f:
                    hasher.update(f.read())
            except OSError:
                hasher.update(chemin.encode("utf-8", errors="ignore"))
        return hasher.hexdigest()

    @staticmethod
    def vectorstore_en_cache(source_hash: Optional[str]) -> bool:
        """Indique si un vectorstore correspondant à `source_hash` est déjà
        disponible (mémoire ou disque), sans le charger. Permet d'éviter de
        parser/chunker le cours.pdf quand ce n'est pas nécessaire."""
        if source_hash is None:
            return False
        if _VECTORSTORE_CACHE["source_hash"] == source_hash and _VECTORSTORE_CACHE["vectorstore"] is not None:
            return True
        if os.path.exists(_INDEX_DIR) and os.path.exists(_HASH_FILE):
            try:
                with open(_HASH_FILE, "r", encoding="utf-8") as f:
                    return f.read().strip() == source_hash
            except OSError:
                return False
        return False

    @staticmethod
    def creer_vectorstore(documents: List[Document], embeddings: HuggingFaceEmbeddings,
                          source_hash: Optional[str] = None) -> FAISS:
        """Crée (ou réutilise) le vector store FAISS.

        Si `source_hash` correspond à celui du dernier vectorstore construit
        (en mémoire ou sauvegardé sur disque via `save_local`), on évite de
        ré-embedder tous les documents et on recharge l'index existant.
        """
        # 1. Réutilisation directe depuis la mémoire du process courant.
        if source_hash is not None and _VECTORSTORE_CACHE["source_hash"] == source_hash \
                and _VECTORSTORE_CACHE["vectorstore"] is not None:
            return _VECTORSTORE_CACHE["vectorstore"]

        # 2. Réutilisation depuis le disque (utile après un redémarrage du
        # serveur, ou entre deux sessions Streamlit distinctes).
        if source_hash is not None and os.path.exists(_INDEX_DIR) and os.path.exists(_HASH_FILE):
            try:
                with open(_HASH_FILE, "r", encoding="utf-8") as f:
                    fichier_hash = f.read().strip()
                if fichier_hash == source_hash:
                    vectorstore = FAISS.load_local(
                        _INDEX_DIR, embeddings, allow_dangerous_deserialization=True
                    )
                    _VECTORSTORE_CACHE["source_hash"] = source_hash
                    _VECTORSTORE_CACHE["vectorstore"] = vectorstore
                    return vectorstore
            except Exception:
                # Index corrompu / incompatible : on retombe sur la
                # reconstruction complète ci-dessous plutôt que de planter.
                pass

        # 3. Reconstruction complète (premier passage, ou fichiers modifiés).
        vectorstore = FAISS.from_documents(
            documents=documents,
            embedding=embeddings
        )

        os.makedirs(DOSSIER_VECTORSTORE, exist_ok=True)
        vectorstore.save_local(_INDEX_DIR)

        if source_hash is not None:
            with open(_HASH_FILE, "w", encoding="utf-8") as f:
                f.write(source_hash)
            _VECTORSTORE_CACHE["source_hash"] = source_hash
            _VECTORSTORE_CACHE["vectorstore"] = vectorstore

        return vectorstore
