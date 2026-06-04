"""Routeur **Historique** : lecture seule de l'historique longitudinal (couche 8).

Expose le ``HistoryStore`` (couche 5, alimenté par le ``JobRunner`` après chaque
run) : la **série** chronologique d'une métrique pour un pipeline/vue, et les
**régressions** (dégradation entre les 2 derniers runs). ``GET`` seuls → pas de
CSRF, pas d'écriture ; pas d'appel réseau → rien à durcir en mode public.
"""

from __future__ import annotations

import dataclasses

from fastapi import APIRouter

from xerocr.adapters.storage.history_store import HistoryStore


def build_history_router(store: HistoryStore) -> APIRouter:
    """Construit le routeur Historique (monté par ``create_app``)."""
    router = APIRouter()

    @router.get("/api/history/series")
    def series(
        pipeline: str, view: str, metric: str = "cer"
    ) -> list[dict[str, object]]:
        """Suite chronologique d'une métrique pour un pipeline sous une vue."""
        return [dataclasses.asdict(r) for r in store.history(pipeline, view, metric)]

    @router.get("/api/history/regressions")
    def regressions(
        view: str, metric: str = "cer", higher_is_better: bool = False
    ) -> list[dict[str, object]]:
        """Pipelines dégradés entre leurs 2 derniers runs (sous une vue/métrique)."""
        found = store.regressions(view, metric, higher_is_better=higher_is_better)
        return [dataclasses.asdict(r) for r in found]

    return router


__all__ = ["build_history_router"]
