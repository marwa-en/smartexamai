
import os
import json
import base64
import pandas as pd
import chromadb
from dotenv import load_dotenv
from chromadb.utils import embedding_functions
from mistralai.client import Mistral
load_dotenv()

API_KEY = os.environ.get("API_KEY")
CSV_PATH = "."
IMAGE_PATH = "."

# Cache process-local : la liste des étudiants (CSV) est la même pour
# toutes les copies d'un même examen. Dans la version d'origine,
# setup_rag() rechargeait le modèle SentenceTransformer et ré-indexait
# tout le CSV dans Chroma à CHAQUE copie corrigée. On ne refait ce travail
# que si le contenu du CSV a effectivement changé.
_RAG_CACHE = {"csv_key": None, "collection": None}


def _hash_fichier(chemin):
    """Empreinte du CONTENU du fichier (et non de sa date de modification) :
    l'app réécrit le CSV uploadé au même chemin à chaque copie corrigée,
    ce qui changerait la date de modification même quand le contenu (la
    liste des étudiants) est identique."""
    import hashlib
    hasher = hashlib.sha256()
    with open(chemin, "rb") as f:
        for bloc in iter(lambda: f.read(65536), b""):
            hasher.update(bloc)
    return hasher.hexdigest()


def setup_rag():
    try:
        csv_key = (os.path.abspath(CSV_PATH), _hash_fichier(CSV_PATH))
    except OSError:
        csv_key = None

    if csv_key is not None and _RAG_CACHE["csv_key"] == csv_key and _RAG_CACHE["collection"] is not None:
        return _RAG_CACHE["collection"]

    embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
    # anonymized_telemetry=False évite l'erreur bénigne mais bruyante
    # "Failed to send telemetry event ... capture() takes 1 positional
    # argument but 3 were given" qui s'affiche sinon dans le terminal à
    # chaque exécution (incompatibilité chromadb / posthog), même si la
    # correction se déroule normalement côté interface.
    client = chromadb.PersistentClient(
        path="./chroma_db",
        settings=chromadb.config.Settings(anonymized_telemetry=False),
    )

    try: client.delete_collection("official_students_db")
    except: pass
    
    collection = client.create_collection(
        name="official_students_db", 
        embedding_function=embed_fn, 
        metadata={"hnsw:space": "cosine"}
    )
    
    df = pd.read_csv(CSV_PATH, sep=",", encoding="utf-8")
    ids, docs, metas = [], [], []
    
    for idx, row in df.iterrows():
        nom, prenom = str(row.get("nom", "")).strip(), str(row.get("prenom", "")).strip()
        cne = str(row.get("cne", "")).strip()
        if not cne or cne == "nan": continue
        
        full_name = f"{nom} {prenom}".strip()
        group, cls = str(row.get("classe", "")).strip(), str(row.get("matiere", "")).strip()
        
        metas.append({"student_id": cne, "name": full_name, "nom": nom, "prenom": prenom, "group": group, "class": cls})
        docs.append(f"{full_name} {cne} {group} {cls}")
        ids.append(f"student_{idx}_{cne}")
        
    for i in range(0, len(ids), 100):
        collection.add(ids=ids[i:i+100], documents=docs[i:i+100], metadatas=metas[i:i+100])

    _RAG_CACHE["csv_key"] = csv_key
    _RAG_CACHE["collection"] = collection
    return collection

def process_image(client, collection):
    
    with open(IMAGE_PATH, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    ext = IMAGE_PATH.split('.')[-1].lower()
    mime = "image/jpeg" if ext in ["jpg", "jpeg"] else f"image/{ext}"
    
    vlm_res = client.chat.complete(
        model="mistral-medium-latest",
        messages=[{"role": "user", "content": [
            {"type": "text", "text": "Transcribe the text from this image exactly. Keep headers and structure."},
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}}
        ]}],
        temperature=0
    )
    raw_text = vlm_res.choices[0].message.content.strip()


    parse_res = client.chat.complete(
        model="mistral-small-latest",
        messages=[{"role": "user", "content": f"Extract student info. Return ONLY valid JSON with keys: 'name', 'student_id', 'group', 'class'. Use null if missing.\n\nTEXT:\n{raw_text[:2000]}"}],
        temperature=0
    )
    parsed = json.loads(parse_res.choices[0].message.content.strip().removeprefix("```json").removesuffix("```").strip())
    
    query = " ".join([str(v) for v in parsed.values() if v])
    results = collection.query(query_texts=[query], n_results=3) if query.strip() else {'metadatas': [[]], 'distances': [[]]}
    candidates = [{**m, "similarity_score": round(1 - d, 3)} for m, d in zip(results['metadatas'][0], results['distances'][0])]
    
    val_prompt = f"""Validate student info extracted from an exam sheet against candidates. Consider OCR errors (0/O, 1/I/l). 
    Select the best match or return NOT_FOUND. Return ONLY valid JSON.
    Extracted: {json.dumps(parsed)}
    Candidates: {json.dumps(candidates)}
    Output Format:
    {{"selected_student": {{"student_id": "", "name": "", "group": ""}}}}"""
    
    val_res = client.chat.complete(model="mistral-small-latest", messages=[{"role": "user", "content": val_prompt}], temperature=0)
    validation = json.loads(val_res.choices[0].message.content.strip().removeprefix("```json").removesuffix("```").strip())
    
    return validation


def main():
    if not os.path.exists(CSV_PATH): raise FileNotFoundError(f"CSV not found: {CSV_PATH}")
    if not os.path.exists(IMAGE_PATH): raise FileNotFoundError(f"Image not found: {IMAGE_PATH}")
    
    collection = setup_rag()
    client = Mistral(api_key=API_KEY)
    
    validation = process_image(client, collection)
    

    final_output = {
        "student": validation.get("selected_student") 
    }
    
 