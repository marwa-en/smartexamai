# 🎓 SmartExamAI

> Plateforme intelligente de **correction automatique d'examens manuscrits** — Vision par ordinateur, VLM, RAG et **sécurité applicative de bout en bout**.

![Python](https://img.shields.io/badge/Python-3.11+-blue) ![FastAPI](https://img.shields.io/badge/FastAPI-API-009688) ![React](https://img.shields.io/badge/React-Vite-61dafb) ![Security](https://img.shields.io/badge/pentest-176%20tests%20%E2%9C%85-ff69b4) ![License](https://img.shields.io/badge/usage-acad%C3%A9mique-lightgrey)

---

## 📌 Table des matières
1. [Objectif](#-objectif)
2. [Fonctionnalités](#-fonctionnalités)
3. [Architecture](#-architecture)
4. [Installation](#-installation)
5. [Premier démarrage & compte administrateur](#-premier-démarrage--compte-administrateur)
6. [Sécurité & tests d'intrusion](#-sécurité--tests-dintrusion)
7. [Capture du résultat](#-capture-du-résultat)
8. [Rapport de pentest](#-rapport-de-pentest)
9. [Détection SOC](#-détection-soc)
10. [Structure du dépôt](#-structure-du-dépôt)
11. [Avertissement légal](#-avertissement-légal)

---

## 🎯 Objectif

Les enseignants consacrent en moyenne **~30 % de leur temps hors classe** à corriger. SmartExamAI automatise la chaîne complète — *scan de la copie → extraction → correction → restitution sécurisée de la note* — tout en laissant **l'enseignant maître de la décision finale**.

Parce que la plateforme manipule des **données sensibles** (copies, barèmes, notes), exécute du **code étudiant** et pilote un **LLM**, la sécurité est une exigence de premier rang. Ce dépôt contient donc, en plus de l'application, une **suite de tests d'intrusion reproductibles** (`pentest/`) et un **kit de détection SOC** (`soc/`).

## ✨ Fonctionnalités

| Domaine | Détails |
|---|---|
| Extraction | Qualité d'image, QR code, segmentation, infos étudiant (RAG), QCM (OpenCV), rédaction (VLM Pixtral), code manuscrit |
| Correction | QCM déterministe · rédaction via RAG · code via **sandbox Docker** + LLM |
| Rôles | Admin / Professeur / Étudiant (JWT + RBAC par ressource) |
| Sécurité | Anti brute-force, CSRF, en-têtes durcis, uploads contrôlés, anti prompt-injection, sandbox isolée |

## 🏗️ Architecture

```
Scan → Qualité → QR → Segmentation ─┬─ Infos étudiant (RAG)
                                    ├─ QCM (Computer Vision)
                                    ├─ Rédaction (VLM + RAG)      → JSON → Correction → Note validée par le prof
                                    └─ Code (VLM + Sandbox Docker)
```

```
.
├── smartexamai-backend/      # API FastAPI + pipeline IA
├── smartexamai-frontend/     # React (Vite)
├── pentest/                  # 🔐 suite de tests d'intrusion (pytest)
├── soc/                      # 🛡️ règles de détection, playbook, mapping MITRE/OWASP
├── docs/                     # rapport de pentest + captures
└── .github/workflows/        # CI sécurité (pytest, bandit, pip-audit, gitleaks)
```

## 🛠️ Installation

### Prérequis
Python ≥ 3.11 · Node ≥ 18 · (optionnel) Docker pour la correction de code et les sondes d'évasion.

### 1. Backend
```bash
cd smartexamai-backend/smartexamai_backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # puis renseigner les variables ci-dessous
uvicorn app.main:app --reload --port 8000
```
Variables importantes (`.env`) :

| Variable | Rôle |
|---|---|
| `SMARTEXAM_JWT_SECRET` | **Obligatoire en prod**, ≥ 32 caractères aléatoires (`python -c "import secrets;print(secrets.token_urlsafe(48))"`) |
| `SMARTEXAM_CORS_ORIGINS` | Liste blanche d'origines (jamais `*` en prod) |
| `SMARTEXAM_ENVIRONMENT` | `development` · `staging` · `production` |
| `OPENROUTER_API_KEY` / `API_KEY` | Clés LLM (ne **jamais** les committer) |

API interactive : <http://localhost:8000/docs> (désactivée en production).

### 2. Frontend
```bash
cd smartexamai-frontend && npm install && npm run dev      # http://localhost:5173
```

## 🔑 Premier démarrage & compte administrateur

Au tout premier lancement, un compte `admin` est créé avec un **mot de passe aléatoire** affiché **une seule fois dans les logs du serveur**. Le changement de mot de passe est **obligatoire** à la première connexion. Il n'existe **aucun identifiant par défaut**.

## 🔐 Sécurité & tests d'intrusion

La suite `pentest/` attaque l'application **en local, sur une base SQLite jetable** (aucune donnée réelle, aucun accès réseau externe).

```bash
pip install -r pentest/requirements-pentest.txt
pytest pentest -v                 # tout lancer
pytest pentest -k "csrf or cors"  # un thème précis
pytest pentest --runxfail         # voir en détail les constats ouverts
```

| Fichier | Couvre | Référentiels |
|---|---|---|
| `test_01_auth_jwt.py` | alg:none, mauvais secret, expiration, confusion d'algo, falsification de rôle | OWASP API2 · MITRE T1550 |
| `test_02_bruteforce_password.py` | 429, verrou de compte, contournement X-Forwarded-For, énumération, timing, politique MDP, SQLi login | MITRE T1110 |
| `test_03_rbac_idor.py` | escalade verticale/horizontale, IDOR, mass-assignment | OWASP API1/API5 |
| `test_04_uploads.py` | extensions, magic bytes, traversal, taille, polyglottes | CWE-434/22 |
| `test_05_llm_security.py` | 17 payloads d'injection FR/EN, 9 techniques d'évasion, bornage, JSON, break-out de prompt | OWASP LLM01/02 · MITRE ATLAS |
| `test_06_sandbox.py` | audit statique Docker (+ sondes live si Docker) | CIS Docker · T1611 |
| `test_07_headers_csrf_cors.py` | en-têtes, CSRF (7 origines hostiles), CORS, garde-fous prod, admin initial | OWASP A05 |
| `test_08_sessions.py` | rotation/rejeu de refresh tokens, révocation, hachage | CWE-613 |
| `test_09_hardening_soc.py` | journaux d'audit, corps malformés, XSS/SQLi, hygiène du dépôt | OWASP A09 · T1562 |

**Convention des constats ouverts** : un test marqué `@finding("F-xx", …)` est un *xfail strict* — la CI reste verte tant que la faille existe, et **échoue dès qu'elle est corrigée** pour t'obliger à retirer le marqueur.

## 📸 Capture du résultat


*Exécution réelle sur le laboratoire local (Python 3.12, SQLite jetable). Détails dans le rapport.*

## 📄 Rapport de pentest

➡️ **[docs/PENTEST_REPORT.md](docs/PENTEST_REPORT.md)** — rapport réalisé sur une **application de laboratoire** (SmartExamAI exécutée localement avec des comptes fictifs). Aucune donnée réelle n'est exposée.

## 🛡️ Détection SOC

Le dossier `soc/` fournit :
- `audit` : événements JSON (`auth.login_failed`, `security.access_denied`, `security.csrf_blocked`…) prêts pour Wazuh / Elastic / Splunk ;
- `sigma/` : 6 règles Sigma (brute-force, password spraying, CSRF, rejeu de jeton, balayage IDOR, prompt injection) ;
- `PLAYBOOK_INCIDENT.md` : procédure de réponse à incident (triage → confinement → éradication → retour d'expérience) ;
- `MITRE_OWASP_MAPPING.md` : correspondance ATT&CK / OWASP Top 10 / OWASP LLM Top 10.

## ⚖️ Avertissement légal

Les tests de ce dépôt sont conçus pour être exécutés **uniquement sur ta propre instance locale de laboratoire**. Ne les dirige jamais vers un système dont tu n'as pas l'autorisation écrite de tester la sécurité.

---
*Projet de fin de stage — IAAI Academy · Spécialité Cybersécurité & Cloud Computing.*
