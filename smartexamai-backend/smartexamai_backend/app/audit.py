"""
SmartExamAI — Journal d'audit de sécurité (SIEM-ready).

Émet des événements JSON (une ligne = un événement) sur le logger « smartexamai.audit ».
Format stable pour être ingéré tel quel par Wazuh / Elastic / Splunk / Loki.
Les mots de passe et jetons ne sont JAMAIS journalisés.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger("smartexamai.audit")

# Champs qu'on refuse catégoriquement d'écrire dans les logs
_FORBIDDEN = {"password", "token", "access_token", "refresh_token", "authorization", "secret"}


def log_event(event: str, *, level: int = logging.WARNING, **fields) -> None:
    """Ex. log_event("auth.login_failed", username="x", ip="1.2.3.4")."""
    safe = {k: v for k, v in fields.items() if k.lower() not in _FORBIDDEN}
    payload = {"ts": datetime.now(timezone.utc).isoformat(), "event": event, **safe}
    logger.log(level, json.dumps(payload, ensure_ascii=False, default=str))
