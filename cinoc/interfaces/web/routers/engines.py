"""Routeur d'aide au composeur (couche 8) : aperçu de normalisation + modèles.

Endpoints **vivants** (consommés par le JS du Banc d'essai) : aperçu de
normalisation (POST, CSRF) et suggestions de modèles par fournisseur (GET). Les
listes de lecture (profils de normalisation/métriques, état des moteurs) sont
rendues **côté serveur** dans les pages — pas d'API JSON dédiée.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from cinoc.app.models import provider_models
from cinoc.app.normalization_preview import (
    NormalizationPreviewError,
    preview_normalization,
)
from cinoc.interfaces.web.security.csrf import csrf_protect


class PreviewRequest(BaseModel):
    """Aperçu de normalisation : un échantillon + un profil **ou** une config YAML."""

    model_config = ConfigDict(extra="forbid")

    sample: str = Field(max_length=4000)
    profile: str | None = Field(default=None, max_length=64)
    config: str | None = Field(default=None, max_length=8000)


def build_engines_router() -> APIRouter:
    """Construit le routeur d'aide au composeur (monté par ``create_app``)."""
    router = APIRouter()

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

    return router


__all__ = ["build_engines_router"]
