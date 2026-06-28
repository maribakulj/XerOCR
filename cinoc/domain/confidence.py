"""``ConfidenceToken`` — schéma du payload ``CONFIDENCES`` (couche 1).

Un jeton de confiance = un mot produit par le moteur + son auto-estimation de
fiabilité dans [0, 1]. Sérialisé en sidecar JSON (liste de jetons) à côté du
texte brut ; consommé par la calibration (couche 3). Type créé **avec** son
premier consommateur (déclencheur du backlog domain atteint).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ConfidenceToken(BaseModel):
    """Mot reconnu + confiance déclarée par le moteur (0 = nulle, 1 = sûre)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    text: str = Field(min_length=1, max_length=256)
    confidence: float = Field(ge=0, le=1)


__all__ = ["ConfidenceToken"]
