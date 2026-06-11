"""``PeroAdapter`` — moteur OCR/HTR réel (pero-ocr).

Local et sans clé : couvre l'imprimé ancien et le manuscrit via les modèles PERO,
là où tesseract couvre l'imprimé moderne. Implémente le ``Module`` Protocol
**directement** — même contrat que le socle, livré in-tree (décision : pas de
discrimination socle/plugin ; seule la livraison diffère). La lib ``pero_ocr`` est
un **extra optionnel** (``xerocr[pero]``), importée **paresseusement** dans
``_invoke_pero`` : importer ce module ne requiert rien ; seule l'exécution exige la
lib + un **modèle** (``model`` = chemin du fichier de config PERO, obligatoire —
pas de modèle embarqué). Sortie : ``RAW_TEXT`` (lignes reconnues, ordre PERO).

**Non déployé au Space** (dép lourde, free-tier) : listé « indisponible » sans
l'extra, comme Kraken — pas d'exécution cloud, pas de clé.
"""

from __future__ import annotations

from pathlib import Path

from xerocr.adapters._workspace import workspace_artifact_path
from xerocr.domain.artifacts import Artifact, ArtifactType, compute_content_hash
from xerocr.domain.errors import AdapterStepError
from xerocr.pipeline.protocols import ParamValue
from xerocr.pipeline.run_control import RunControl
from xerocr.pipeline.types import RunContext, StepOutput

_VERSION = "1.0"


def _invoke_pero(  # pragma: no cover -- lib + modèle requis (cf. 'live')
    *, image_path: str, config_path: str
) -> str:
    """Mise en page + reconnaissance PERO → texte (lignes jointes, ordre PERO)."""
    try:
        import configparser

        import cv2  # type: ignore[import-not-found]
        from pero_ocr.document_ocr.layout import (  # type: ignore[import-not-found]
            PageLayout,
        )
        from pero_ocr.document_ocr.page_parser import (  # type: ignore[import-not-found]
            PageParser,
        )
    except ImportError as exc:
        raise AdapterStepError(
            "pero : lib non installée (pip install 'xerocr[pero]')."
        ) from exc
    config = configparser.ConfigParser()
    if not config.read(config_path):
        raise AdapterStepError(f"pero : config illisible {config_path!r}.")
    image = cv2.imread(image_path)
    if image is None:
        raise AdapterStepError(f"pero : image illisible {image_path!r}.")
    parser = PageParser(config, config_path=str(Path(config_path).parent))
    layout = PageLayout(id="page", page_size=(image.shape[0], image.shape[1]))
    layout = parser.process_page(image, layout)
    lines = [
        str(line.transcription)
        for region in layout.regions
        for line in region.lines
        if line.transcription
    ]
    return "\n".join(lines).strip()


class PeroAdapter:
    """OCR/HTR PERO : ``IMAGE`` → ``RAW_TEXT`` (lignes reconnues)."""

    def __init__(self, *, label: str, model: str) -> None:
        if not label or not all(c.isalnum() or c in "_-" for c in label):
            raise AdapterStepError(f"pero : label invalide {label!r}.")
        if not model:
            raise AdapterStepError(
                "pero : paramètre 'model' (chemin de config PERO) requis."
            )
        self._label = label
        self._model = model

    @property
    def name(self) -> str:
        return f"pero:{self._label}"

    @property
    def version(self) -> str:
        return _VERSION

    @property
    def input_types(self) -> frozenset[ArtifactType]:
        return frozenset({ArtifactType.IMAGE})

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
        image = inputs.get(ArtifactType.IMAGE)
        if image is None or image.uri is None:
            raise AdapterStepError(
                f"{self.name} : artefact IMAGE manquant ou sans URI."
            )
        if context.workspace_uri is None:
            raise AdapterStepError(f"{self.name} : workspace requis.")
        text = _invoke_pero(image_path=image.uri, config_path=self._model)
        output_path = workspace_artifact_path(
            context.workspace_uri, context.document_id, self._label, "txt"
        )
        output_path.write_text(text, encoding="utf-8")
        return StepOutput(
            artifacts={
                ArtifactType.RAW_TEXT: Artifact(
                    id=f"{context.document_id}:{self.name}:raw_text",
                    document_id=context.document_id,
                    type=ArtifactType.RAW_TEXT,
                    uri=str(output_path),
                    content_hash=compute_content_hash(text.encode("utf-8")),
                )
            }
        )


__all__ = ["PeroAdapter"]
