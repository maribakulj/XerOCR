"""Observabilité Prometheus **opt-in** (couche 8) — compteur de requêtes HTTP.

Activée **seulement si demandée** (``create_app(metrics=…)`` ou env
``XEROCR_METRICS``) : un Space exposé ne fuit pas ses statistiques par défaut. On
compte les requêtes par ``(méthode, statut)`` — **cardinalité basse** (jamais le
chemin brut, qui exploserait la cardinalité) — et on les expose au format texte
Prometheus sur ``/metrics``. État **par application** (aucun global de module → la
factory ``create_app`` reste respectée), **thread-safe** (le ``JobRunner`` sert en
parallèle). Sans dépendance externe : l'exposition est un format texte stable.
"""

from __future__ import annotations

import threading
from collections import Counter

from starlette.types import ASGIApp, Message, Receive, Scope, Send

_CONTENT_TYPE = "text/plain; version=0.0.4; charset=utf-8"


class RequestMetrics:
    """Compteur **thread-safe** de requêtes HTTP par ``(méthode, statut)``."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counts: Counter[tuple[str, int]] = Counter()

    def record(self, method: str, status: int) -> None:
        with self._lock:
            self._counts[(method, status)] += 1

    def render(self) -> str:
        """Exposition Prometheus (texte) — **déterministe** (clés triées)."""
        lines = [
            "# HELP xerocr_requests_total Total HTTP requests handled.",
            "# TYPE xerocr_requests_total counter",
        ]
        with self._lock:
            items = sorted(self._counts.items())
        for (method, status), count in items:
            lines.append(
                f"xerocr_requests_total"
                f'{{method="{method}",status="{status}"}} {count}'
            )
        return "\n".join(lines) + "\n"

    @property
    def content_type(self) -> str:
        return _CONTENT_TYPE


class MetricsMiddleware:
    """Enregistre méthode + statut final de chaque requête HTTP (ASGI pur)."""

    def __init__(self, app: ASGIApp, metrics: RequestMetrics) -> None:
        self._app = app
        self._metrics = metrics

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return
        method = str(scope.get("method", "GET"))

        async def send_counting(message: Message) -> None:
            if message["type"] == "http.response.start":
                self._metrics.record(method, int(message["status"]))
            await send(message)

        await self._app(scope, receive, send_counting)


__all__ = ["MetricsMiddleware", "RequestMetrics"]
