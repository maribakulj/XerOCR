"""``RunContext`` — contexte d'exécution propagé à chaque ``Module.execute``.

Porte l'identité du document, la version de code (provenance), le nom de la
pipeline et la ``Deadline`` coopérative. Concern d'exécution → couche 4 ; fait
paire avec ``RunControl`` (raison pour laquelle il ne vit pas en ``domain``).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from pydantic import BaseModel, ConfigDict, Field

from xerocr.domain.artifacts import Artifact, ArtifactType
from xerocr.domain.deadline import Deadline
from xerocr.domain.usage import ResourceUsage


class RunContext(BaseModel):
    """Contexte d'exécution d'une étape, pour un document donné.

    Immuable. La ``Deadline`` se sérialise via ``remaining_seconds`` (cf.
    ``domain.deadline``), donc reste transposable entre process.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    document_id: str = Field(min_length=1, max_length=256)
    code_version: str = Field(min_length=1, max_length=128)
    pipeline_name: str = Field(min_length=1, max_length=128)
    workspace_uri: str | None = Field(default=None, max_length=2048)
    deadline: Deadline = Field(default_factory=Deadline.infinite)


@dataclass(frozen=True)
class StepOutput:
    """Sortie d'un ``Module.execute`` : artefacts produits + consommation.

    ``artifacts`` contient tous les ``output_types`` déclarés (contrat module).
    ``usage`` ne porte que ce que le module **sait** (jetons d'un appel LLM) —
    la durée de l'étape est mesurée par l'**exécuteur**, jamais par le module.
    """

    artifacts: Mapping[ArtifactType, Artifact]
    usage: ResourceUsage | None = None


@dataclass(frozen=True)
class DocumentExecution:
    """Résultat de l'exécution d'une pipeline sur **un** document.

    ``artifacts`` est le pool final (dernier artefact par type) ; ``usage``
    agrège durées et jetons de toutes les étapes (somme ``None``-tolérante).
    """

    artifacts: Mapping[ArtifactType, Artifact]
    usage: ResourceUsage = field(default_factory=ResourceUsage)


__all__ = ["DocumentExecution", "RunContext", "StepOutput"]
