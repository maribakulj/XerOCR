"""Routeur « Moteurs » : disponibilité runtime des moteurs (couche 8).

``GET /api/engines`` — **lecture seule**, alimente l'onglet « Moteurs » réservé
Restitue l'état calculé par ``app.engines`` (sondes bon marché, mode
public reflété). Aucune écriture → pas de CSRF.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from xerocr.app.engines import StatusProvider, normalization_profiles
from xerocr.app.models import provider_models
from xerocr.app.normalization_preview import (
    NormalizationPreviewError,
    preview_normalization,
)
from xerocr.app.run_planning import metric_profile_catalog
from xerocr.interfaces.web.security.csrf import csrf_protect


class PreviewRequest(BaseModel):
    """Aperçu de normalisation : un échantillon + un profil **ou** une config YAML."""

    model_config = ConfigDict(extra="forbid")

    sample: str = Field(max_length=4000)
    profile: str | None = Field(default=None, max_length=64)
    config: str | None = Field(default=None, max_length=8000)


def build_engines_router(provider: StatusProvider) -> APIRouter:
    """Construit le routeur « Moteurs » (monté par ``create_app``)."""
    router = APIRouter()

    @router.get("/api/normalization/profiles")
    def list_normalization_profiles() -> dict[str, list[str]]:
        """Profils de comparaison disponibles — lus dynamiquement (couche 2)."""
        return {"profiles": list(normalization_profiles())}

    @router.post(
        "/api/normalization/preview", dependencies=[Depends(csrf_protect)]
    )
    def preview(req: PreviewRequest) -> dict[str, str]:
        """Normalise un échantillon par un profil nommé OU une config YAML custom.

        **Sans persistance** : la config custom est appliquée à la volée, jamais
        stockée. Profil inconnu / config invalide → ``422`` (jamais un défaut muet)."""
        try:
            normalized = preview_normalization(
                req.sample, profile=req.profile, config=req.config
            )
        except NormalizationPreviewError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return {"normalized": normalized}

    @router.get("/api/models/{model_provider}")
    def list_models(model_provider: str) -> dict[str, object]:
        """Modèles canoniques d'un fournisseur + capacité vision (suggestions UI).

        Fournisseur inconnu → liste vide (200) : le champ ``model`` reste libre."""
        return {
            "provider": model_provider,
            "models": [m.model_dump() for m in provider_models(model_provider)],
        }

    @router.get("/api/engines")
    def list_engines() -> dict[str, list[dict[str, object]]]:
        return {"engines": [status.model_dump() for status in provider()]}

    @router.get("/api/metric-profiles")
    def list_metric_profiles() -> dict[str, list[dict[str, object]]]:
        """Profils de métriques proposables au lanceur (source unique, couche 6).

        Lecture seule (pas de CSRF) ; ``standard`` d'abord. Le profil choisi
        atterrit sur ``LaunchRequest.metric_profile`` (résolu au plan)."""
        return {"profiles": list(metric_profile_catalog())}

    return router


__all__ = ["build_engines_router"]
