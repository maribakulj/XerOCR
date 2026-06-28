"""Squelette commun des adapters OCR « image → un seul RAW_TEXT » (couche 5).

Le même ``execute()`` était recopié dans chaque adapter OCR mono-sortie : sonde
d'annulation, garde IMAGE, garde workspace, écriture du ``.txt`` dans le workspace,
construction de l'artefact ``RAW_TEXT`` (id ``{doc}:{name}:raw_text`` + hash du
texte). On le mutualise ici (miroir de ``llm/_base``) ; le **détail moteur** (params,
clé API, deadline) reste dans chaque adapter, porté par la closure ``recognize``.

N'est PAS pour les adapters multi-sorties (``tesseract`` : RAW_TEXT + CONFIDENCES
+ ALTO optionnel) — eux gardent leur ``execute()`` propre. Contrat de l'artefact
``RAW_TEXT`` figé par ``tests/adapters/test_ocr_artifact_contract_anchor``.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping

from cinoc.adapters._workspace import workspace_artifact_path
from cinoc.domain.artifacts import Artifact, ArtifactType, compute_content_hash
from cinoc.domain.errors import AdapterStepError
from cinoc.pipeline.run_control import RunControl
from cinoc.pipeline.types import RunContext, StepOutput


def run_image_to_text(
    *,
    name: str,
    label: str,
    inputs: Mapping[ArtifactType, Artifact],
    context: RunContext,
    control: RunControl,
    recognize: Callable[[str], str],
) -> StepOutput:
    """Exécute un OCR image → ``RAW_TEXT`` unique, gardes + persistance mutualisées.

    ``recognize(image_uri) -> texte`` porte la reconnaissance réelle (et ses gardes
    propres : clé API, modèle…). Ordre identique à l'ancien code par adapter :
    annulation → IMAGE → workspace → ``recognize`` → écriture ``.txt`` → artefact.
    """
    control.raise_if_cancelled()
    image = inputs.get(ArtifactType.IMAGE)
    if image is None or image.uri is None:
        raise AdapterStepError(f"{name} : artefact IMAGE manquant ou sans URI.")
    if context.workspace_uri is None:
        raise AdapterStepError(f"{name} : workspace requis.")
    text = recognize(image.uri)
    output_path = workspace_artifact_path(
        context.workspace_uri, context.document_id, label, "txt"
    )
    output_path.write_text(text, encoding="utf-8")
    return StepOutput(
        artifacts={
            ArtifactType.RAW_TEXT: Artifact(
                id=f"{context.document_id}:{name}:raw_text",
                document_id=context.document_id,
                type=ArtifactType.RAW_TEXT,
                uri=str(output_path),
                content_hash=compute_content_hash(text.encode("utf-8")),
            )
        }
    )


__all__ = ["run_image_to_text"]
