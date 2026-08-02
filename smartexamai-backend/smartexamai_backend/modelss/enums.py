"""SmartExamAI — Enumérations partagées entre les modèles."""
from __future__ import annotations

import enum


class RoleUtilisateur(str, enum.Enum):
    ADMIN = "admin"
    PROFESSEUR = "professeur"
    ETUDIANT = "etudiant"


class StatutCopie(str, enum.Enum):
    DEPOSEE = "deposee"
    EN_CORRECTION = "en_correction"
    CORRIGEE = "corrigee"
    ERREUR = "erreur"


class StatutResultat(str, enum.Enum):
    SUCCES = "succes"
    ECHEC = "echec"


class SystemeNotationQCM(str, enum.Enum):
    NORMAL = "normal"
    CANADIEN = "canadian"
