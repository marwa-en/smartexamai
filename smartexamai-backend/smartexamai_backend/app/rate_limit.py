"""
SmartExamAI — Rate limiting en mémoire pour la protection brute-force.

⚠️ En production multi-workers, remplacer par Redis.
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Deque, Dict

from configss.settings import settings


@dataclass
class RateLimitConfig:
    max_attempts: int = 5
    window_seconds: int = 300  # 5 minutes


@dataclass
class SlidingWindowLimiter:
    """Limiteur de débit basé sur une fenêtre glissante."""

    config: RateLimitConfig = field(default_factory=RateLimitConfig)
    _requests: Dict[str, Deque[float]] = field(default_factory=lambda: defaultdict(deque))
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def is_allowed(self, key: str) -> bool:
        now = time.monotonic()
        window_start = now - self.config.window_seconds

        with self._lock:
            timestamps = self._requests[key]

            # Supprimer les entrées expirées
            while timestamps and timestamps[0] < window_start:
                timestamps.popleft()

            if len(timestamps) >= self.config.max_attempts:
                return False

            timestamps.append(now)
            return True

    def reset(self, key: str) -> None:
        with self._lock:
            self._requests.pop(key, None)


# Instance globale
login_limiter = SlidingWindowLimiter(
    config=RateLimitConfig(max_attempts=5, window_seconds=300)
)