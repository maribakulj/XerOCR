"""Provenance d'un artefact.

Empreinte minimale attachée à chaque ``Artifact`` produit par une étape
de pipeline. Permet la reproductibilité : même corpus + même
``code_version`` + même ``parameters_hash`` = mêmes artefacts à hash près.
"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field


class ProvenanceRecord(BaseModel):
    """Empreinte de production d'un artefact.

    Immuable : pour modifier une provenance, on crée un nouvel artefact.

    Attributs
    ---------
    timestamp:
        Date/heure UTC de production (défaut : maintenant).
    code_version:
        Version du code qui a produit l'artefact. Str opaque.
    parameters_hash:
        Hash SHA-256 hex des paramètres de l'étape. ``None`` autorisé
        pour les artefacts initiaux (image fournie, GT lue).
    """

    model_config = ConfigDict(frozen=True)

    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC),
    )
    code_version: str
    parameters_hash: str | None = None

    def is_compatible_with(self, other: ProvenanceRecord) -> bool:
        """Deux artefacts produits par le même contexte de calcul.

        Le timestamp n'entre pas dans la comparaison — seule la
        combinaison ``(code_version, parameters_hash)`` détermine la
        compatibilité de cache.
        """
        return (
            self.code_version == other.code_version
            and self.parameters_hash == other.parameters_hash
        )


__all__ = ["ProvenanceRecord"]
