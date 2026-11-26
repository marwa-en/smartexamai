"""Service de nettoyage des documents"""
import re
import os
from typing import List
from langchain_core.documents import Document
DOSSIER_TEMP = "data/_temp_pipeline"
PARAMETRES_NETTOYAGE = {
    "supprimer_numeros_page": True,
    "supprimer_lignes_numerotees": True,
    "supprimer_copyright": True,
    "supprimer_en_tetes_universite": True,
    "reduire_sauts_ligne": True,
    "supprimer_espaces_fins": True,
    "supprimer_lignes_vides_excessives": True,
    "longueur_min_ligne": 3,
}
DOSSIER_NETTOYAGE = os.path.join(DOSSIER_TEMP, "nettoyage")


class CleanerService:
    """Service responsable du nettoyage des textes."""
    
    @staticmethod
    def nettoyer_texte(texte: str) -> str:
        """Nettoie le texte selon les paramètres."""
        p = PARAMETRES_NETTOYAGE
        
        if p["supprimer_numeros_page"]:
            texte = re.sub(r'[Pp]age\s+\d+(\s*(/|sur)\s*\d+)?', '', texte)
            texte = re.sub(r'^\s*\d{1,3}\s*$', '', texte, flags=re.MULTILINE)
        
        if p["supprimer_lignes_numerotees"]:
            texte = re.sub(r'^\s*\d+\s*$', '', texte, flags=re.MULTILINE)
        
        if p["supprimer_copyright"]:
            texte = re.sub(r'©.*', '', texte)
            texte = re.sub(r'[Cc]opyright.*', '', texte)
            texte = re.sub(r'[Tt]ous droits réservés.*', '', texte)
        
        if p["supprimer_en_tetes_universite"]:
            texte = re.sub(r'^.*[Uu]niversité.*$', '', texte, flags=re.MULTILINE)
            texte = re.sub(r'^.*[Ff]aculté.*$', '', texte, flags=re.MULTILINE)
            texte = re.sub(r'^.*[Dd]épartement.*$', '', texte, flags=re.MULTILINE)
        
        if p["reduire_sauts_ligne"]:
            texte = re.sub(r'\n{3,}', '\n\n', texte)
        
        if p["supprimer_espaces_fins"]:
            lignes = texte.split('\n')
            lignes = [ligne.strip() for ligne in lignes]
            texte = '\n'.join(lignes)
        
        if p["supprimer_lignes_vides_excessives"]:
            lignes = texte.split('\n')
            lignes_filtrees = []
            for ligne in lignes:
                if (ligne == '' or 
                    len(ligne) >= p["longueur_min_ligne"] or
                    ligne.startswith('#') or
                    (ligne.isupper() and len(ligne) < 50)):
                    lignes_filtrees.append(ligne)
            texte = '\n'.join(lignes_filtrees)
        
        texte = texte.strip()
        return re.sub(r'\n{3,}', '\n\n', texte)
    
    @staticmethod
    def nettoyer_et_sauvegarder(documents: List[Document], categorie: str) -> List[Document]:
        """Nettoie et sauvegarde les documents."""
        os.makedirs(DOSSIER_NETTOYAGE, exist_ok=True)
        docs_nettoyes = []
        
        for i, doc in enumerate(documents):
            contenu_nettoye = CleanerService.nettoyer_texte(doc.page_content)
            nom_sortie = f"nettoye_{categorie}_{i}.txt"
            chemin_sortie = os.path.join(DOSSIER_NETTOYAGE, nom_sortie)
            
            with open(chemin_sortie, "w", encoding="utf-8") as f:
                f.write(contenu_nettoye)
            
            doc_nettoye = Document(
                page_content=contenu_nettoye,
                metadata={
                    "categorie": categorie,
                    "source": doc.metadata.get("source", "?"),
                    "chemin_fichier_nettoye": chemin_sortie,
                },
            )
            docs_nettoyes.append(doc_nettoye)
        
        return docs_nettoyes