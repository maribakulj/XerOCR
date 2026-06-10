"""``GoogleVisionAdapter`` — OCR cloud (Google Cloud Vision REST), facturé à l'image.

Moteur cloud **first-party**. On vise l'**API REST** (``httpx``) plutôt que le SDK
``google-cloud-vision`` (gRPC + auth ADC service-account, lourd et difficile à
rejouer) : transport léger, **testable par cassette HTTP**, auth par **clé d'API**
(``GOOGLE_VISION_API_KEY``). Implémente le ``Module`` Protocol **directement** ;
``httpx`` est l'extra ``xerocr[google]``, importé **paresseusement** dans
``_invoke_google_vision`` (mockable, CI sans clé ni réseau).

Sortie : ``fullTextAnnotation.text`` de ``DOCUMENT_TEXT_DETECTION`` — le texte
dense d'une page (le bon mode pour des documents, ≠ ``TEXT_DETECTION`` épars).
"""

from __future__ import annotations

import os
from base64 import b64encode
from pathlib import Path
from typing import TYPE_CHECKING

from xerocr.adapters._workspace import workspace_artifact_path
from xerocr.domain.artifacts import Artifact, ArtifactType, compute_content_hash
from xerocr.domain.deadline import Deadline
from xerocr.domain.errors import AdapterStepError
from xerocr.pipeline.protocols import ParamValue
from xerocr.pipeline.run_control import RunControl
from xerocr.pipeline.types import RunContext, StepOutput

if TYPE_CHECKING:  # annotations seules — pas d'import httpx au chargement du module
    import httpx

_VERSION = "1.0"
_ENDPOINT = "https://vision.googleapis.com/v1/images:annotate"
_API_KEY_ENV = "GOOGLE_VISION_API_KEY"
_FEATURE = "DOCUMENT_TEXT_DETECTION"


def _extract_text(payload: object) -> str:
    """Texte de la 1ʳᵉ réponse Vision ; erreur par image → ``AdapterStepError``.

    Forme : ``{"responses": [{"fullTextAnnotation": {"text": …}}]}`` (ou
    ``{"error": {"message": …}}`` pour un échec par image). Aucun texte détecté
    (page blanche) → ``""`` — un résultat valide, pas une erreur.
    """
    if not isinstance(payload, dict):
        raise AdapterStepError("google_vision : réponse JSON inattendue (objet).")
    responses = payload.get("responses")
    if not isinstance(responses, list) or not responses:
        raise AdapterStepError("google_vision : réponse sans 'responses'.")
    first = responses[0]
    if not isinstance(first, dict):
        raise AdapterStepError("google_vision : 'responses[0]' inattendu.")
    error = first.get("error")
    if isinstance(error, dict) and error:
        message = error.get("message", "erreur sans message")
        raise AdapterStepError(f"google_vision : erreur API : {message}")
    annotation = first.get("fullTextAnnotation")
    if isinstance(annotation, dict):
        text = annotation.get("text")
        return str(text).strip() if text else ""
    return ""


def _invoke_google_vision(
    *,
    image_path: str,
    deadline: Deadline,
    api_key: str,
    transport: httpx.BaseTransport | None = None,
) -> str:
    """POST l'image à Vision et renvoie le texte. ``transport`` injecté → cassette.

    Endpoint **fixe et de confiance** (Google) : pas de durcissement anti-SSRF (≠
    importeurs de corpus, dont l'URL vient de l'utilisateur). La clé d'API est en
    *query string* (jamais journalisée : les messages d'erreur ne portent que le
    statut). ``httpx`` paresseux : importer ce module n'exige pas l'extra.
    """
    try:
        import httpx
    except ImportError as exc:
        raise AdapterStepError(
            "google_vision : httpx non installé (pip install 'xerocr[google]')."
        ) from exc
    content = b64encode(Path(image_path).read_bytes()).decode("ascii")
    body = {
        "requests": [
            {"image": {"content": content}, "features": [{"type": _FEATURE}]}
        ]
    }
    try:
        with httpx.Client(
            timeout=deadline.as_sdk_timeout(), transport=transport
        ) as client:
            response = client.post(_ENDPOINT, params={"key": api_key}, json=body)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as exc:
        raise AdapterStepError(
            f"google_vision : statut HTTP {exc.response.status_code}."
        ) from exc
    except httpx.HTTPError as exc:
        raise AdapterStepError(
            f"google_vision : échec de transport : {type(exc).__name__}."
        ) from exc
    return _extract_text(data)


class GoogleVisionAdapter:
    """OCR cloud Google Vision : ``IMAGE`` → ``RAW_TEXT`` (texte dense de la page)."""

    def __init__(self, *, label: str) -> None:
        if not label or not all(c.isalnum() or c in "_-" for c in label):
            raise AdapterStepError(f"google_vision : label invalide {label!r}.")
        self._label = label

    @property
    def name(self) -> str:
        return f"google_vision:{self._label}"

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
        api_key = os.environ.get(_API_KEY_ENV)
        if not api_key:
            raise AdapterStepError(f"{self.name} : {_API_KEY_ENV} manquante.")
        text = _invoke_google_vision(
            image_path=image.uri, deadline=context.deadline, api_key=api_key
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


__all__ = ["GoogleVisionAdapter"]
