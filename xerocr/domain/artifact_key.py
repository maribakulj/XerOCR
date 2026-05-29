"""``ArtifactKey`` — clé canonique multi-paramètres du cache d'artefacts.

Type pur (dataclass frozen, sérialisation déterministe, calcul de hash).
La couche ``pipeline`` doit pouvoir calculer une clé pour interroger le
cache sans importer ``adapters`` — d'où sa place en couche 1.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ArtifactKey:
    """Composition immuable des paramètres qui déterminent l'identité
    d'un artefact dans le store. Sérialisable JSON déterministe.

    ``input_hashes`` : tuple ``((type, content_hash), …)`` des inputs.
    ``None`` ou hash vide → la clé n'est pas calculable.
    """

    input_hashes: tuple[tuple[str, str], ...] = field(default_factory=tuple)
    adapter_name: str = ""
    adapter_version: str | None = None
    step_params: dict[str, str | int | float | bool] = field(default_factory=dict)
    code_version: str = ""
    normalization_profile: str | None = None
    projection_name: str | None = None
    projection_params: dict[str, str | int | float | bool] = field(
        default_factory=dict,
    )
    metric_version: str | None = None

    def to_canonical_json(self) -> str:
        """Sérialise la clé en JSON déterministe.

        Clés triées, ``ensure_ascii=False`` (Unicode brut préservé),
        séparateurs compacts (variations de whitespace minimisées).
        """
        sorted_inputs = sorted(self.input_hashes)
        payload = {
            "inputs": sorted_inputs,
            "adapter": self.adapter_name,
            "adapter_version": self.adapter_version,
            "step_params": self.step_params,
            "code_version": self.code_version,
            "normalization_profile": self.normalization_profile,
            "projection_name": self.projection_name,
            "projection_params": self.projection_params,
            "metric_version": self.metric_version,
        }
        return json.dumps(
            payload,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        )

    def hash_hex(self) -> str | None:
        """Clé hex SHA-256 (64 chars).

        Retourne ``None`` si un seul ``input_hash`` est ``None`` ou vide —
        convention « ne pas servir un résultat de cache douteux ».
        """
        for _, h in self.input_hashes:
            if h is None or h == "":
                return None
        canonical = self.to_canonical_json()
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


__all__ = ["ArtifactKey"]
