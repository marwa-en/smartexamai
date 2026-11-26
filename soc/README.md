# soc/

Kit de détection et de réponse de SmartExamAI.

- `sigma/` : 6 règles de détection (format Sigma) alimentées par le journal d'audit JSON (`app/audit.py`).
- `MITRE_OWASP_MAPPING.md` : menace → test → règle de détection.
- `PLAYBOOK_INCIDENT.md` : réponse à incident (détecter, qualifier, contenir, éradiquer, rétablir, retour d'expérience).
