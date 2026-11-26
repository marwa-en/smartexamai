# SmartExamAI — Backend FastAPI + Frontend React

> Plateforme intelligente de correction d'examens manuscrits, basée sur la Vision par Ordinateur, les Vision Language Models (VLM), le Retrieval-Augmented Generation (RAG) et la sécurité.

---

## Vue d'ensemble

SmartExamAI automatise l'extraction et la correction du contenu de copies d'examens manuscrites.

L'état actuel du projet est le suivant :

- **Backend** : une **API REST FastAPI** (JWT, rôles admin/professeur/étudiant), qui réutilise tel quel le cœur métier existant (SQLAlchemy, repositories, services, pipeline IA de correction).
- **Frontend** : une **application React (Vite)**, connectée en temps réel à l'API, reprenant le design système existant (thèmes par rôle, composants, tableaux, cartes).

Le cœur du pipeline IA (extraction OCR/segmentation, RAG, VLM, validation de code) provient du moteur d'extraction historique du projet et est réutilisé sans modification par l'API.

```
.
├── smartexamai-backend/          # API FastAPI + pipeline IA (Python)
│   ├── smartexamai_backend/
│   │   ├── app/                  # API FastAPI
│   │   ├── modelss/ repositories/ service/ core/ db/ configss/ storage/
│   │   ├── ai_pipeline/ integration/   # pipeline de correction (inchangé)
│   │   └── cli.py                # ancien CLI (conservé, toujours utilisable)
│   ├── correction/ extraction/ segmentatio/ pretraitement/  # modules IA (inchangés)
│   └── orchestrator.py
├── smartexamai-frontend/         # application React (Vite)
│   └── src/
└── HANDOFF.md                    # état d'avancement détaillé / suite éventuelle
```

---

## Démarrage rapide

### 1. Backend (FastAPI)

```bash
cd smartexamai-backend/smartexamai_backend
python3 -m venv .venv && source .venv/bin/activate      # optionnel mais recommandé
pip install -r requirements.txt --break-system-packages  # ou sans ce flag dans un venv
cp .env.example .env      # puis ajustez si besoin (clé JWT, clés API LLM, etc.)
uvicorn app.main:app --reload --port 8000
```

- Documentation interactive : http://localhost:8000/docs
- Un compte administrateur par défaut est créé automatiquement au premier démarrage : **username `admin` / mot de passe `ChangeMe123!`** (à changer immédiatement via `PATCH /api/admin/users/{id}`).
- Base de données par défaut : SQLite (`smartexamai.db`, créé automatiquement). Pour Postgres/MySQL, changez `SMARTEXAM_DATABASE_URL` dans `.env`.

### 2. Frontend (React)

```bash
cd smartexamai-frontend
npm install
npm run dev
```

- Ouvrez http://localhost:5173
- En développement, le proxy Vite (`vite.config.js`) redirige automatiquement `/api/*` vers `http://localhost:8000` : aucune configuration CORS/URL supplémentaire n'est nécessaire.
- Connectez-vous avec le compte admin par défaut ci-dessus (le rôle sélectionné sur l'écran de connexion ne sert qu'au thème visuel — le vrai rôle vient du compte).

### 3. Build de production du frontend

```bash
cd smartexamai-frontend
VITE_API_URL=https://votre-api.exemple.com npm run build
```

Le dossier `dist/` généré peut être servi par n'importe quel serveur statique (Nginx, Caddy, `serve`, etc.) ou par le même serveur que l'API.

---

## Fonctionnalités

- Authentification JWT et contrôle des rôles (admin/professeur/étudiant)
- Endpoints CRUD pour utilisateurs, classes, matières, examens
- Dépôt de copies (upload multipart)
- Déclenchement de la correction IA (unitaire et en lot)
- Gestion des ressources pédagogiques par le professeur
- Consultation/validation/ajustement des notes
- Consultation des notes et téléchargement du relevé côté étudiant
- Vérification automatique de la qualité des images, détection de flou et de QR Code
- Segmentation automatique de la copie (informations étudiant, QCM, rédaction, code)
- Extraction des informations étudiant via RAG
- Extraction des QCM par Computer Vision (détection de marqueurs, homographie, détection des bulles)
- Extraction des rédactions manuscrites via un Vision Language Model (Pixtral Large)
- Extraction du code source manuscrit avec validation syntaxique

---

## Architecture du pipeline IA (réutilisé tel quel)

```
                          Images de la copie
                               │
                               ▼
                  Vérification de la qualité d'image
                               │
                               ▼
                       Détection QR Code
                               │
                               ▼
                    Segmentation automatique
                               │
      ┌──────────────┬──────────────┬──────────────┬──────────────┐
      ▼              ▼              ▼              ▼
 Infos étudiant      QCM         Rédaction      Code source
      │              │              │              │
      ▼              ▼              ▼              ▼
        Prétraitement des images (dédié à chaque section)
      │              │              │              │
      ▼              ▼              ▼              ▼
           Modèles d'extraction dédiés
      │              │              │              │
      └──────────────┴──────────────┴──────────────┘
                               │
                               ▼
                        JSON structuré
```

Sortie du pipeline : quatre fichiers JSON indépendants (`info.json`, `qcm.json`, `redaction.json`, `code.json`), consommés ensuite par les endpoints de correction de l'API.

---

## Technologies

- Python, FastAPI, SQLAlchemy, JWT
- React (Vite), react-router-dom
- OpenCV, NumPy
- API Mistral AI, Pixtral Large
- Retrieval-Augmented Generation (RAG)
- ORB Feature Matching, RANSAC, détection de QR Code

---

## Ce qui a été fait

- API FastAPI complète, testée avec `TestClient` (login, CRUD, contrôle des rôles).
- Frontend React avec routing par rôle, contexte d'authentification, layout fidèle au design fourni.
- Testé bout en bout via les serveurs de développement réels (proxy Vite → FastAPI → SQLite), build de production du frontend vérifié sans erreur.
- Toute la couche métier existante (`modelss/`, `repositories/`, `service/`, `core/`, `db/`, `storage/`, `ai_pipeline/`, `integration/`) a été réutilisée sans modification ; l'ancien CLI (`cli.py`) reste utilisable en parallèle.
