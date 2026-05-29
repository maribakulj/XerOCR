"""``PipelineStep``, ``PipelineSpec``, ``PipelineMode``.

Description purement déclarative d'un DAG de transformation documentaire.
Sérialisable YAML, validable sans instancier les modules concrets.

``PipelineStep`` ne porte qu'un ``adapter_name`` (str) ; le mapping
nom → instance est maintenu par un service applicatif et résolu au moment
de l'exécution, pas de la spec. Bénéfice : le YAML est versionnable
indépendamment de l'environnement Python, et la validation s'exécute sans
instancier aucun module.
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from xerocr.domain.artifacts import ArtifactType

# Identifiant d'étape : alphanum + ``_-``. Nom court lisible dans les logs
# et le rapport.
_STEP_ID_RE = re.compile(r"^[A-Za-z0-9_\-]+$")

#: Modes canoniques d'un pipeline OCR+LLM (source de vérité unique).
#:
#: - ``text_only`` — l'OCR amont produit un texte, le LLM le corrige sans
#:   voir l'image.
#: - ``text_and_image`` — le VLM corrige le texte en s'appuyant sur l'image.
#: - ``zero_shot`` — pas d'OCR amont ; un VLM transcrit l'image directement.
PipelineMode = Literal["text_only", "text_and_image", "zero_shot"]

#: Sentinel pour ``inputs_from`` désignant les artefacts initiaux fournis
#: au runner (typiquement ``IMAGE``).
INITIAL_STEP_ID = "__initial__"


class PipelineStep(BaseModel):
    """Une étape déclarative dans un DAG de pipeline.

    Attributs
    ---------
    id:
        Identifiant unique dans la pipeline (alphanum + ``_-``).
    kind:
        Catégorie informationnelle (``"ocr"``, ``"segmentation"``,
        ``"post_correction"``…). Label libre en ``snake_case``.
    adapter_name:
        Nom de l'adapter dans le registre runtime. Convention
        ``"<provider>:<engine_or_model>"``.
    params:
        Paramètres passés à l'adapter (chaque adapter valide les siens).
    input_types / output_types:
        Types consommés / produits, validés contre les étapes voisines.
    inputs_from:
        DAG branchant : pour chaque type d'entrée, l'étape source.
        ``"__initial__"`` désigne les entrées initiales du runner. Dict
        vide → version la plus récente de chaque type.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(min_length=1, max_length=128)
    kind: str = Field(min_length=1, max_length=64)
    adapter_name: str = Field(min_length=1, max_length=256)
    params: dict[str, str | int | float | bool] = Field(default_factory=dict)
    input_types: tuple[ArtifactType, ...] = Field(default_factory=tuple)
    output_types: tuple[ArtifactType, ...] = Field(default_factory=tuple)
    inputs_from: dict[ArtifactType, str] = Field(default_factory=dict)

    @field_validator("id")
    @classmethod
    def _validate_step_id(cls, v: str) -> str:
        if not _STEP_ID_RE.match(v):
            from xerocr.domain.errors import XerOCRError

            raise XerOCRError(
                f"step id invalide : {v!r}. Doit matcher {_STEP_ID_RE.pattern!r} "
                "(alphanum + _-)."
            )
        if v == INITIAL_STEP_ID:
            from xerocr.domain.errors import XerOCRError

            raise XerOCRError(
                f"step id réservé : {INITIAL_STEP_ID!r} désigne les entrées "
                "initiales du runner."
            )
        return v


class PipelineSpec(BaseModel):
    """DAG déclaratif d'une pipeline composée.

    Sérialisable via ``model_dump()`` + ``yaml.safe_dump``, chargeable via
    ``model_validate(yaml.safe_load(text))``.

    ``steps`` est ordonné par dépendance topologique : si ``s2`` dépend de
    ``s1``, alors ``s1`` apparaît avant ``s2``.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(min_length=1, max_length=128)
    description: str = ""
    initial_inputs: tuple[ArtifactType, ...] = Field(default_factory=tuple)
    steps: tuple[PipelineStep, ...] = Field(default_factory=tuple)

    def step_by_id(self, step_id: str) -> PipelineStep | None:
        for s in self.steps:
            if s.id == step_id:
                return s
        return None


__all__ = ["PipelineMode", "PipelineSpec", "PipelineStep", "INITIAL_STEP_ID"]
