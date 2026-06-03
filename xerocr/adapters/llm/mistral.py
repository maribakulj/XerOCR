"""``MistralAdapter`` — post-correction LLM via l'API Mistral (mode ``text_only``).

Implémente le ``Module`` Protocol : ``RAW_TEXT`` → ``CORRECTED_TEXT``. La clé API
vient de ``MISTRAL_API_KEY`` (secret de Space) ; le SDK ``mistralai`` est un
**extra** importé paresseusement dans ``_invoke_mistral`` (isolé → **mockable**,
CI sans clé ni réseau). La ``Deadline`` borne l'appel.
"""

from __future__ import annotations

from xerocr.adapters.llm._base import (
    DEFAULT_CORRECTION_PROMPT,
    build_prompt,
    load_ocr_text,
    normalize_llm_content,
    validate_llm_label,
    write_corrected,
)
from xerocr.domain.artifacts import Artifact, ArtifactType
from xerocr.domain.deadline import Deadline
from xerocr.domain.errors import AdapterStepError
from xerocr.pipeline.protocols import ParamValue
from xerocr.pipeline.run_control import RunControl
from xerocr.pipeline.types import RunContext

_VERSION = "1.0"
_DEFAULT_MODEL = "mistral-small-latest"


def _invoke_mistral(  # pragma: no cover -- réseau + clé API (cf. marqueur 'live')
    *, model: str, prompt: str, deadline: Deadline
) -> str:
    import os

    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        raise AdapterStepError("mistral : MISTRAL_API_KEY manquante.")
    try:
        from mistralai import Mistral  # type: ignore[import-not-found]
    except ImportError as exc:
        raise AdapterStepError(
            "mistral : SDK non installé (pip install 'xerocr[mistral]')."
        ) from exc
    client_kwargs: dict[str, object] = {"api_key": api_key}
    timeout = deadline.as_sdk_timeout()
    if timeout is not None:
        client_kwargs["timeout_ms"] = int(timeout * 1000)
    try:
        client = Mistral(**client_kwargs)
        response = client.chat.complete(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
        )
    except Exception as exc:  # le SDK lève des erreurs HTTP/SDK variées
        raise AdapterStepError(
            f"mistral a échoué ({model}) : {type(exc).__name__}: {exc}"
        ) from exc
    if not response.choices:
        return ""
    return normalize_llm_content(response.choices[0].message.content)


class MistralAdapter:
    """Post-correction LLM Mistral : ``RAW_TEXT`` → ``CORRECTED_TEXT``."""

    def __init__(
        self,
        *,
        label: str,
        model: str = _DEFAULT_MODEL,
        prompt: str = DEFAULT_CORRECTION_PROMPT,
    ) -> None:
        self._label = validate_llm_label(label, "MistralAdapter")
        self._model = model
        self._prompt = prompt

    @property
    def name(self) -> str:
        return f"mistral:{self._label}"

    @property
    def version(self) -> str:
        return _VERSION

    @property
    def input_types(self) -> frozenset[ArtifactType]:
        return frozenset({ArtifactType.RAW_TEXT})

    @property
    def output_types(self) -> frozenset[ArtifactType]:
        return frozenset({ArtifactType.CORRECTED_TEXT})

    def execute(
        self,
        inputs: dict[ArtifactType, Artifact],
        params: dict[str, ParamValue],
        context: RunContext,
        control: RunControl,
    ) -> dict[ArtifactType, Artifact]:
        control.raise_if_cancelled()
        if context.workspace_uri is None:
            raise AdapterStepError(
                f"{self.name} : workspace requis (RunContext.workspace_uri)."
            )
        ocr_text = load_ocr_text(inputs, self.name)
        prompt = build_prompt(self._prompt, ocr_text)
        corrected = _invoke_mistral(
            model=self._model, prompt=prompt, deadline=context.deadline
        )
        return write_corrected(
            context.workspace_uri,
            context.document_id,
            self._label,
            self.name,
            corrected,
        )


__all__ = ["MistralAdapter"]
