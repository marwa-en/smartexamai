"""Service de chargement des documents"""
import os
from typing import List
from langchain_community.document_loaders import (
    PyPDFLoader, TextLoader, UnstructuredWordDocumentLoader,
)
from langchain_core.documents import Document

EXTENSIONS_AUTORIZES = {".pdf", ".txt", ".md", ".docx"}

class LoaderService:
    """Service responsable du chargement des fichiers."""
    
    @staticmethod
    def charger_fichier(chemin: str, categorie: str) -> List[Document]:
        """Charge un fichier selon son extension."""
        ext = os.path.splitext(chemin)[1].lower()
        nom_fichier = os.path.basename(chemin)
        
        if ext == ".pdf":
            loader = PyPDFLoader(chemin)
        elif ext in [".txt", ".md"]:
            loader = TextLoader(chemin, encoding="utf-8")
        elif ext == ".docx":
            loader = UnstructuredWordDocumentLoader(chemin)
        else:
            raise ValueError(f"Format non supporté : {ext}")
        
        documents = loader.load()
        for doc in documents:
            doc.metadata["categorie"] = categorie
            doc.metadata["source"] = nom_fichier
            doc.metadata["chemin"] = chemin
        
        return documents
    
    @staticmethod
    def valider_chemin(chemin: str) -> tuple[bool, str]:
        """Valide un chemin de fichier."""
        chemin = chemin.strip().strip('"').strip("'")
        
        if not os.path.exists(chemin):
            return False, f"Fichier introuvable : {chemin}"
        
        if not os.path.isfile(chemin):
            return False, f"Ce n'est pas un fichier : {chemin}"
        
        ext = os.path.splitext(chemin)[1].lower()
        if ext not in EXTENSIONS_AUTORIZES:
            return False, f"Format non supporté : {ext}"
        
        return True, ""