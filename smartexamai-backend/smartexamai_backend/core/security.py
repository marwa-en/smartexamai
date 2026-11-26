"""
SmartExamAI — Hachage et vérification des mots de passe.

Utilise PBKDF2-HMAC-SHA256 (bibliothèque standard `hashlib`),
afin de ne dépendre d'aucun package tiers pour une fonction aussi critique.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets

from configss.settings import settings

_ALGORITHM = "sha256"
_SALT_BYTES = 16


def hash_password(plain_password: str) -> str:
    """Retourne une chaîne au format 'algo$iterations$salt_hex$hash_hex'."""
    salt = secrets.token_bytes(_SALT_BYTES)
    iterations = settings.password_hash_iterations
    derived = hashlib.pbkdf2_hmac(
        _ALGORITHM, plain_password.encode("utf-8"), salt, iterations
    )
    return f"{_ALGORITHM}${iterations}${salt.hex()}${derived.hex()}"


def verify_password(plain_password: str, stored_hash: str) -> bool:
    """Vérifie un mot de passe en clair contre un hash stocké."""
    try:
        algorithm, iterations_str, salt_hex, hash_hex = stored_hash.split("$")
        iterations = int(iterations_str)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
    except (ValueError, AttributeError):
        return False

    derived = hashlib.pbkdf2_hmac(
        algorithm, plain_password.encode("utf-8"), salt, iterations
    )
    return hmac.compare_digest(derived, expected)
