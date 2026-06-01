"""Limiteur de débit HTTP **en mémoire** (couche 8).

Fenêtre fixe par IP cliente : au-delà de ``max_requests`` requêtes sur
``window_seconds``, renvoie ``429``. Suffisant pour borner une vitrine mono-worker
(le Space). **Limites assumées** (documentées, pas masquées) : non distribué
(état par process) → en multi-worker chaque worker compte séparément ; pour un
vrai cluster il faudrait un store partagé.

Dette corrigée au portage (cf. analyse couche 8, constat H) : les compteurs
d'IP inactives sont **purgés** (fenêtre expirée) → pas de fuite mémoire lente.
Thread-safe (``Lock``) car uvicorn peut servir plusieurs requêtes en parallèle.
"""

from __future__ import annotations

import threading
import time

from starlette.types import ASGIApp, Receive, Scope, Send

#: Réponse 429 minimale (ASGI brut), sans corps sensible.
_TOO_MANY = {
    "type": "http.response.start",
    "status": 429,
    "headers": [(b"content-type", b"text/plain; charset=utf-8")],
}


class RateLimitMiddleware:
    """Fenêtre fixe par IP ; ``429`` au dépassement. Purge les IP expirées."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        max_requests: int = 60,
        window_seconds: float = 60.0,
    ) -> None:
        if max_requests < 1 or window_seconds <= 0:
            raise ValueError("rate limit : max_requests>=1 et window_seconds>0.")
        self._app = app
        self._max = max_requests
        self._window = window_seconds
        self._lock = threading.Lock()
        #: ip -> (début de fenêtre, compteur).
        self._hits: dict[str, tuple[float, int]] = {}

    def _client_ip(self, scope: Scope) -> str:
        client = scope.get("client")
        if isinstance(client, (tuple, list)) and client:
            return str(client[0])
        return "unknown"

    def _allow(self, ip: str, now: float) -> bool:
        with self._lock:
            self._prune(now)
            start, count = self._hits.get(ip, (now, 0))
            if now - start >= self._window:
                start, count = now, 0  # fenêtre expirée → réinitialisation
            if count >= self._max:
                return False
            self._hits[ip] = (start, count + 1)
            return True

    def _prune(self, now: float) -> None:
        """Retire les IP dont la fenêtre est expirée (anti-fuite mémoire)."""
        expired = [
            ip
            for ip, (start, _) in self._hits.items()
            if now - start >= self._window
        ]
        for ip in expired:
            del self._hits[ip]

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return
        if self._allow(self._client_ip(scope), time.monotonic()):
            await self._app(scope, receive, send)
            return
        await send(_TOO_MANY)
        await send(
            {"type": "http.response.body", "body": b"rate limit exceeded"}
        )


__all__ = ["RateLimitMiddleware"]
