"""``MistralOCRAdapter`` — OCR cloud (API Mistral OCR), facturé à la page.

Premier moteur **payant à la page** du socle : donne un sens réel à l'axe
coût du Pareto (économie T10, tarif ``cloud_page_kinds``). Implémente le
``Module`` Protocol ; SDK ``mistralai`` = extra (``xerocr[mistral]``), importé
paresseusement dans ``_invoke_mistral_ocr`` (mockable, CI sans clé ni réseau).
Clé ``MISTRAL_API_KEY``. Sortie : le texte (markdown) des pages, concaténé.
"""

from __future__ import annotations

from base64 import b64encode
from pathlib import Path

from xerocr.adapters._workspace import workspace_artifact_path
from xerocr.domain.artifacts import Artifact, ArtifactType, compute_content_hash
from xerocr.domain.deadline import Deadline
from xerocr.domain.errors import AdapterStepError
from xerocr.pipeline.protocols import ParamValue
from xerocr.pipeline.run_control import RunControl
from xerocr.pipeline.types import RunContext, StepOutput

_VERSION = "1.0"
_DEFAULT_MODEL = "mistral-ocr-latest"
_MEDIA = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
          ".webp": "image/webp", ".tif": "image/tiff", ".tiff": "image/tiff"}


def _invoke_mistral_ocr(  # pragma: no cover -- réseau + clé API (cf. 'live')
    *, model: str, image_path: str, deadline: Deadline
) -> str:
    import os

    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        raise AdapterStepError("mistral_ocr : MISTRAL_API_KEY manquante.")
    try:
        from mistralai import Mistral  # type: ignore[import-not-found]
    except ImportError as exc:
        raise AdapterStepError(
            "mistral_ocr : SDK non installé (pip install 'xerocr[mistral]')."
        ) from exc
    path = Path(image_path)
    media = _MEDIA.get(path.suffix.lower(), "image/png")
    image_b64 = b64encode(path.read_bytes()).decode("ascii")
    client_kwargs: dict[str, object] = {"api_key": api_key}
    timeout = deadline.as_sdk_timeout()
    if timeout is not None:
        client_kwargs["timeout_ms"] = int(timeout * 1000)
    try:
        client = Mistral(**client_kwargs)  # type: ignore[arg-type]
        response = client.ocr.process(
            model=model,
            document={
                "type": "image_url",
                "image_url": f"data:{media};base64,{image_b64}",
            },
        )
    except Exception as exc:  # le SDK lève des erreurs HTTP/SDK variées
        raise AdapterStepError(
            f"mistral_ocr a échoué ({model}) : {type(exc).__name__}: {exc}"
        ) from exc
    pages = getattr(response, "pages", None) or []
    return "\n\n".join(
        str(getattr(page, "markdown", "") or "") for page in pages
    ).strip()


class MistralOCRAdapter:
    """OCR cloud Mistral : ``IMAGE`` → ``RAW_TEXT`` (markdown des pages)."""

    def __init__(self, *, label: str, model: str = _DEFAULT_MODEL) -> None:
        if not label or not all(c.isalnum() or c in "_-" for c in label):
            raise AdapterStepError(f"mistral_ocr : label invalide {label!r}.")
        self._label = label
        self._model = model

    @property
    def name(self) -> str:
        return f"mistral_ocr:{self._label}"

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
        text = _invoke_mistral_ocr(
            model=self._model, image_path=image.uri, deadline=context.deadline
        )
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


__all__ = ["MistralOCRAdapter"]
