"""Routeur « Moteurs » : disponibilité runtime des moteurs (couche 8).

``GET /api/engines`` — **lecture seule**, alimente l'onglet « Moteurs » réservé
dès TU1. Restitue l'état calculé par ``app.engines`` (sondes bon marché, mode
public reflété). Aucune écriture → pas de CSRF.
"""

from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter

from xerocr.app.engines import EngineStatus

#: Fournit l'état courant des moteurs (capturé par ``create_app`` avec le mode).
StatusProvider = Callable[[], tuple[EngineStatus, ...]]


def build_engines_router(provider: StatusProvider) -> APIRouter:
    """Construit le routeur « Moteurs » (monté par ``create_app``)."""
    router = APIRouter()

    @router.get("/api/engines")
    def list_engines() -> dict[str, list[dict[str, object]]]:
        return {"engines": [status.model_dump() for status in provider()]}

    return router


__all__ = ["build_engines_router"]
