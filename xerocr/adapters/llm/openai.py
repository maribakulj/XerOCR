"""``OpenAIAdapter`` — post-correction LLM via l'API OpenAI (mode ``text_only``).

Implémente le ``Module`` Protocol : ``RAW_TEXT`` → ``CORRECTED_TEXT``. La clé API
vient de ``OPENAI_API_KEY`` ; le SDK ``openai`` est un **extra** importé
paresseusement dans ``_invoke_openai`` (isolé → **mockable**, CI sans clé ni
réseau). La ``Deadline`` borne l'appel (timeout SDK) ; l'annulation fine via
``register_cancel_handle`` est la référence ``ollama`` (tranche suivante).
"""

from __future__ import annotations

from xerocr.adapters.llm._base import (
    DEFAULT_CORRECTION_PROMPT,
    build_prompt,
    load_ocr_text,
    normalize_llm_content,
    write_corrected,
)
from xerocr.domain.artifacts import Artifact, ArtifactType
from xerocr.domain.deadline import Deadline
from xerocr.domain.errors import AdapterStepError
from xerocr.pipeline.protocols import ParamValue
from xerocr.pipeline.run_control import RunControl
from xerocr.pipeline.types import RunContext

_VERSION = "1.0"
_DEFAULT_MODEL = "gpt-4o-mini"


def _invoke_openai(  # pragma: no cover -- réseau + clé API (cf. marqueur 'live')
    *, model: str, prompt: str, deadline: Deadline
) -> str:
    import os

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise AdapterStepError("openai : OPENAI_API_KEY manquante.")
    try:
        from openai import OpenAI, OpenAIError  # type: ignore[import-not-found]
    except ImportError as exc:
        raise AdapterStepError(
            "openai : SDK non installé (pip install 'xerocr[openai]')."
        ) from exc
    kwargs: dict[str, object] = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0,
    }
    timeout = deadline.as_sdk_timeout()
    if timeout is not None:
        kwargs["timeout"] = timeout
    try:
        response = OpenAI(api_key=api_key).chat.completions.create(**kwargs)
    except OpenAIError as exc:
        raise AdapterStepError(
            f"openai a échoué ({model}) : {type(exc).__name__}: {exc}"
        ) from exc
    if not response.choices:
        return ""
    return normalize_llm_content(response.choices[0].message.content)


class OpenAIAdapter:
    """Post-correction LLM OpenAI : ``RAW_TEXT`` → ``CORRECTED_TEXT``."""

    def __init__(
        self,
        *,
        label: str,
        model: str = _DEFAULT_MODEL,
        prompt: str = DEFAULT_CORRECTION_PROMPT,
    ) -> None:
        if not label or not all(c.isalnum() or c in "_-" for c in label):
            raise AdapterStepError(
                f"OpenAIAdapter : label invalide {label!r} (alphanum + _ -)."
            )
        self._label = label
        self._model = model
        self._prompt = prompt

    @property
    def name(self) -> str:
        return f"openai:{self._label}"

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
        corrected = _invoke_openai(
            model=self._model, prompt=prompt, deadline=context.deadline
        )
        return write_corrected(
            context.workspace_uri,
            context.document_id,
            self._label,
            self.name,
            corrected,
        )


__all__ = ["OpenAIAdapter"]
