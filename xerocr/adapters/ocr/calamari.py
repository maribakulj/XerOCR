"""``CalamariAdapter`` — moteur OCR réel (calamari-ocr, reconnaissance de lignes).

Local et sans clé. Implémente le ``Module`` Protocol **directement** — même
contrat que le socle, livré in-tree (pas de discrimination socle/plugin). La lib
``calamari_ocr`` est un **extra optionnel** (``xerocr[calamari]``), importée
**paresseusement** dans ``_invoke_calamari`` : importer ce module ne requiert rien ;
seule l'exécution exige la lib + un **modèle** (``model`` = checkpoint, obligatoire).

Calamari reconnaît une **ligne** par image : utilisé seul sur une page, il traite
l'image comme une ligne unique ; son usage naturel est en **recognizer par
région** dans le pipeline de segmentation (fan-out par bloc). Sortie : ``RAW_TEXT``.

**Non déployé au Space** (dép lourde TensorFlow, free-tier) : listé « indisponible »
sans l'extra, comme Kraken/PERO.
"""

from __future__ import annotations

from xerocr.adapters._workspace import workspace_artifact_path
from xerocr.domain.artifacts import Artifact, ArtifactType, compute_content_hash
from xerocr.domain.errors import AdapterStepError
from xerocr.pipeline.protocols import ParamValue
from xerocr.pipeline.run_control import RunControl
from xerocr.pipeline.types import RunContext, StepOutput

_VERSION = "1.0"


def _invoke_calamari(  # pragma: no cover -- lib + modèle requis (cf. 'live')
    *, image_path: str, model_path: str
) -> str:
    """Reconnaissance Calamari de l'image (ligne) → texte prédit."""
    try:
        import numpy as np  # type: ignore[import-not-found]
        from calamari_ocr.ocr.predict.predictor import (  # type: ignore[import-not-found]
            Predictor,
            PredictorParams,
        )
        from PIL import Image  # type: ignore[import-not-found]
    except ImportError as exc:
        raise AdapterStepError(
            "calamari : lib non installée (pip install 'xerocr[calamari]')."
        ) from exc
    try:
        predictor = Predictor.from_checkpoint(
            params=PredictorParams(), checkpoint=model_path
        )
    except (OSError, ValueError, RuntimeError) as exc:  # loader calamari
        raise AdapterStepError(
            f"calamari : modèle illisible {model_path!r} : {exc}"
        ) from exc
    image = np.array(Image.open(image_path).convert("L"))
    predictions = predictor.predict_raw([image])
    texts = [str(prediction.sentence) for prediction in predictions]
    return " ".join(texts).strip()


class CalamariAdapter:
    """OCR Calamari : ``IMAGE`` → ``RAW_TEXT`` (texte de la ligne reconnue)."""

    def __init__(self, *, label: str, model: str) -> None:
        if not label or not all(c.isalnum() or c in "_-" for c in label):
            raise AdapterStepError(f"calamari : label invalide {label!r}.")
        if not model:
            raise AdapterStepError(
                "calamari : paramètre 'model' (checkpoint) requis."
            )
        self._label = label
        self._model = model

    @property
    def name(self) -> str:
        return f"calamari:{self._label}"

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
        text = _invoke_calamari(image_path=image.uri, model_path=self._model)
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


__all__ = ["CalamariAdapter"]
