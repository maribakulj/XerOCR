"""Routeur « Moteurs » : disponibilité runtime des moteurs (couche 8).

``GET /api/engines`` — **lecture seule**, alimente l'onglet « Moteurs » réservé
Restitue l'état calculé par ``app.engines`` (sondes bon marché, mode
public reflété). Aucune écriture → pas de CSRF.
"""

from __future__ import annotations

from fastapi import APIRouter

from xerocr.app.engines import StatusProvider, normalization_profiles


def build_engines_router(provider: StatusProvider) -> APIRouter:
    """Construit le routeur « Moteurs » (monté par ``create_app``)."""
    router = APIRouter()

    @router.get("/api/normalization/profiles")
    def list_normalization_profiles() -> dict[str, list[str]]:
        """Profils de comparaison disponibles — lus dynamiquement (couche 2)."""
        return {"profiles": list(normalization_profiles())}


    @router.get("/api/engines")
    def list_engines() -> dict[str, list[dict[str, object]]]:
        return {"engines": [status.model_dump() for status in provider()]}

    return router


__all__ = ["build_engines_router"]
