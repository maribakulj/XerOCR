"""``LayoutToTextExtractor`` — ``LAYOUT rempli → RAW_TEXT`` (couche 5).

Quatrième étage **optionnel** d'un pipeline hybride : une fois les régions
reconnues (fan-out → ``CanonicalLayout`` rempli), on aplatit le texte dans
**l'ordre de lecture** pour le rendre **scorable** comme n'importe quelle sortie
``RAW_TEXT`` (CER/WER à la page). C'est ce qui permet à un run « segmenteur →
reconnaissance par bloc » d'être un **concurrent du Banc d'essai** comparé à un
OCR à plat, et plus seulement un ALTO produit dans son coin.

Déterministe : ordre = ``reading_order`` de la page (repli sur l'ordre déclaré),
lignes d'une région jointes par ``\\n``, régions par ``\\n``, pages par ``\\n``.
"""

from __future__ import annotations

from pathlib import Path

from cinoc.domain.artifacts import Artifact, ArtifactType, compute_content_hash
from cinoc.domain.errors import AdapterStepError
from cinoc.domain.layout import CanonicalLayout, LayoutPage
from cinoc.pipeline.protocols import ParamValue
from cinoc.pipeline.run_control import RunControl
from cinoc.pipeline.types import RunContext, StepOutput

_VERSION = "1.0"


def _page_text(page: LayoutPage) -> str:
    """Texte d'une page, régions dans l'ordre de lecture (repli ordre déclaré)."""
    by_id = {region.id: region for region in page.regions}
    ordered = [by_id[rid] for rid in page.reading_order if rid in by_id]
    seen = {region.id for region in ordered}
    ordered.extend(region for region in page.regions if region.id not in seen)
    blocks: list[str] = []
    for region in ordered:
        lines = "\n".join(line.text for line in region.lines if line.text)
        if lines:
            blocks.append(lines)
    return "\n".join(blocks)


class LayoutToTextExtractor:
    """Aplatit un ``LAYOUT`` rempli en ``RAW_TEXT`` (ordre de lecture, déterministe)."""

    def __init__(self, label: str) -> None:
        self._label = label

    @property
    def name(self) -> str:
        return f"layout_to_text:{self._label}"

    @property
    def version(self) -> str:
        return _VERSION

    @property
    def input_types(self) -> frozenset[ArtifactType]:
        return frozenset({ArtifactType.LAYOUT})

    @property
    def output_types(self) -> frozenset[ArtifactType]:
        return frozenset({ArtifactType.RAW_TEXT})

    def execute(
        self,
        inputs: dict[ArtifactType, Artifact],
        params: dict[str, ParamValue],
        context: RunContext,
        control: RunControl,
    ) -> StepOutput:
        control.raise_if_cancelled()
        layout_art = inputs.get(ArtifactType.LAYOUT)
        if layout_art is None or layout_art.uri is None:
            raise AdapterStepError(
                f"{self.name} : artefact LAYOUT manquant ou sans URI."
            )
        layout_path = Path(layout_art.uri)
        try:
            layout = CanonicalLayout.model_validate_json(layout_path.read_bytes())
        except (OSError, ValueError) as exc:
            raise AdapterStepError(
                f"{self.name} : LAYOUT illisible ({layout_path.name!r}) : {exc}"
            ) from exc
        text = "\n".join(_page_text(page) for page in layout.pages)
        payload = text.encode("utf-8")
        out_dir = (
            Path(context.workspace_uri)
            if context.workspace_uri
            else layout_path.parent
        )
        out_path = out_dir / f"{context.document_id.replace('/', '_')}.layout.txt"
        out_path.write_bytes(payload)
        return StepOutput(
            artifacts={
                ArtifactType.RAW_TEXT: Artifact(
                    id=f"{context.document_id}:{self.name}:raw_text",
                    document_id=context.document_id,
                    type=ArtifactType.RAW_TEXT,
                    uri=str(out_path),
                    content_hash=compute_content_hash(payload),
                )
            }
        )


__all__ = ["LayoutToTextExtractor"]
