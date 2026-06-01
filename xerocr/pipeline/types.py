"""``RunContext`` — contexte d'exécution propagé à chaque ``Module.execute``.

Porte l'identité du document, la version de code (provenance), le nom de la
pipeline et la ``Deadline`` coopérative. Concern d'exécution → couche 4 ; fait
paire avec ``RunControl`` (raison pour laquelle il ne vit pas en ``domain``).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from xerocr.domain.deadline import Deadline


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


__all__ = ["RunContext"]
