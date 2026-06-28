"""Cache TTL minimal, thread-safe (couche 8 — UX).

Mémoïse un résultat coûteux (fetch réseau d'un catalogue de découverte) pendant
une fenêtre courte, pour ne pas refetch à **chaque** chargement de page. Horloge
**injectable** (``clock``) → testable sans dormir. Aucun effet de bord à l'import.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import Generic, TypeVar

K = TypeVar("K")
V = TypeVar("V")


class TTLCache(Generic[K, V]):
    """Cache clé→valeur à expiration (TTL). Recalcule à la demande après péremption.

    Best-effort : si ``compute`` lève, **rien n'est mis en cache** et l'exception
    remonte (un échec réseau ne fige pas une valeur fautive).
    """

    def __init__(
        self, ttl_seconds: float, *, clock: Callable[[], float] = time.monotonic
    ) -> None:
        self._ttl = ttl_seconds
        self._clock = clock
        self._entries: dict[K, tuple[float, V]] = {}
        self._lock = threading.Lock()

    def get_or_compute(self, key: K, compute: Callable[[], V]) -> V:
        """Retourne la valeur cachée si fraîche, sinon ``compute()`` (et la cache)."""
        now = self._clock()
        with self._lock:
            hit = self._entries.get(key)
            if hit is not None and hit[0] > now:
                return hit[1]
        # Calcul **hors verrou** (le fetch peut être lent) : on ne sérialise pas
        # les requêtes ; une course bénigne recalcule au pire deux fois.
        value = compute()
        with self._lock:
            self._entries[key] = (now + self._ttl, value)
        return value


__all__ = ["TTLCache"]
