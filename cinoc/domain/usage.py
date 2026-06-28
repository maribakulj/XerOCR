"""``ResourceUsage`` — consommation mesurée d'une exécution (couche 1).

Vocabulaire transversal : la couche 4 (exécuteur) mesure la durée et collecte
les jetons remontés par les modules LLM/VLM ; la couche 3 (``RunResult``) porte
l'agrégat par (pipeline × document). Les durées sont du **wall-clock** : comme
les horodatages du ``RunManifest``, elles sont une mesure d'environnement,
exclues de l'identité des artefacts (déterminisme — voir ``ProvenanceRecord``).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


def _add(a: int | None, b: int | None) -> int | None:
    if a is None and b is None:
        return None
    return (a or 0) + (b or 0)


class ResourceUsage(BaseModel):
    """Durée et jetons consommés. ``None`` = non mesuré / non applicable."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    #: Durée wall-clock en secondes (mesurée par l'exécuteur, jamais par le
    #: module — source unique).
    duration_seconds: float | None = Field(default=None, ge=0)
    #: Jetons d'entrée/sortie d'un appel LLM/VLM (remontés par l'adapter quand
    #: le fournisseur les expose ; ``None`` pour un moteur non facturé au jeton).
    tokens_in: int | None = Field(default=None, ge=0)
    tokens_out: int | None = Field(default=None, ge=0)

    def merged_with(self, other: ResourceUsage | None) -> ResourceUsage:
        """Somme champ à champ (``None``-tolérante) — agrégation par document."""
        if other is None:
            return self
        duration: float | None
        if self.duration_seconds is None and other.duration_seconds is None:
            duration = None
        else:
            duration = (self.duration_seconds or 0.0) + (
                other.duration_seconds or 0.0
            )
        return ResourceUsage(
            duration_seconds=duration,
            tokens_in=_add(self.tokens_in, other.tokens_in),
            tokens_out=_add(self.tokens_out, other.tokens_out),
        )


__all__ = ["ResourceUsage"]
