"""``AnthropicAdapter`` — post-correction LLM **et** transcription VLM (Claude).

Implémente le ``Module`` Protocol, trois modes (``PipelineMode``) selon le rôle :
``text_only`` (texte → corrigé), ``text_and_image`` (Claude vision : image +
texte → corrigé), ``zero_shot`` (Claude vision : image → texte). Clé
``ANTHROPIC_API_KEY`` ; SDK ``anthropic`` = **extra** importé paresseusement dans
``_invoke_anthropic`` / ``_invoke_anthropic_vision`` (isolés → **mockables**, CI
sans clé ni réseau). La ``Deadline`` borne l'appel.
"""

from __future__ import annotations

from xerocr.adapters.llm._base import (
    default_prompt_for_role,
    llm_input_types,
    llm_output_type,
    normalize_llm_content,
    run_llm_step,
    validate_llm_label,
    validate_role,
)
from xerocr.domain.artifacts import Artifact, ArtifactType
from xerocr.domain.deadline import Deadline
from xerocr.domain.errors import AdapterStepError
from xerocr.domain.pipeline import PipelineMode
from xerocr.pipeline.protocols import ParamValue
from xerocr.pipeline.run_control import RunControl
from xerocr.pipeline.types import RunContext

_VERSION = "1.0"
_DEFAULT_MODEL = "claude-haiku-4-5-20251001"
_MAX_TOKENS = 4096
_SUPPORTED: frozenset[str] = frozenset({"text_only", "text_and_image", "zero_shot"})


def _anthropic_client(  # pragma: no cover -- réseau + clé API (cf. 'live')
    model: str, content: object, deadline: Deadline
) -> str:
    """Appel ``messages.create`` partagé (texte ou multimodal)."""
    import os

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise AdapterStepError("anthropic : ANTHROPIC_API_KEY manquante.")
    try:
        from anthropic import (  # type: ignore[import-not-found]
            Anthropic,
            AnthropicError,
        )
    except ImportError as exc:
        raise AdapterStepError(
            "anthropic : SDK non installé (pip install 'xerocr[anthropic]')."
        ) from exc
    client_kwargs: dict[str, object] = {"api_key": api_key}
    timeout = deadline.as_sdk_timeout()
    if timeout is not None:
        client_kwargs["timeout"] = timeout
    try:
        client = Anthropic(**client_kwargs)
        response = client.messages.create(
            model=model,
            max_tokens=_MAX_TOKENS,
            messages=[{"role": "user", "content": content}],
        )
    except AnthropicError as exc:
        raise AdapterStepError(
            f"anthropic a échoué ({model}) : {type(exc).__name__}: {exc}"
        ) from exc
    return normalize_llm_content(response.content)


def _invoke_anthropic(  # pragma: no cover -- réseau + clé API (cf. marqueur 'live')
    *, model: str, prompt: str, deadline: Deadline
) -> str:
    return _anthropic_client(model, prompt, deadline)


def _invoke_anthropic_vision(  # pragma: no cover -- réseau + clé API (cf. 'live')
    *, model: str, prompt: str, media_type: str, image_b64: str, deadline: Deadline
) -> str:
    content = [
        {"type": "text", "text": prompt},
        {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": image_b64,
            },
        },
    ]
    return _anthropic_client(model, content, deadline)


class AnthropicAdapter:
    """Adapter Anthropic multi-mode (post-correction texte/image, transcription)."""

    def __init__(
        self,
        *,
        label: str,
        model: str = _DEFAULT_MODEL,
        role: str = "text_only",
        prompt: str | None = None,
    ) -> None:
        self._label = validate_llm_label(label, "AnthropicAdapter")
        self._model = model
        self._role: PipelineMode = validate_role(role, "AnthropicAdapter", _SUPPORTED)
        self._prompt = (
            prompt if prompt is not None else default_prompt_for_role(self._role)
        )

    @property
    def name(self) -> str:
        return f"anthropic:{self._label}"

    @property
    def version(self) -> str:
        return _VERSION

    @property
    def input_types(self) -> frozenset[ArtifactType]:
        return llm_input_types(self._role)

    @property
    def output_types(self) -> frozenset[ArtifactType]:
        return frozenset({llm_output_type(self._role)})

    def execute(
        self,
        inputs: dict[ArtifactType, Artifact],
        params: dict[str, ParamValue],
        context: RunContext,
        control: RunControl,
    ) -> dict[ArtifactType, Artifact]:
        def text_invoke(prompt: str) -> str:
            return _invoke_anthropic(
                model=self._model, prompt=prompt, deadline=context.deadline
            )

        def vision_invoke(prompt: str, media_type: str, image_b64: str) -> str:
            return _invoke_anthropic_vision(
                model=self._model,
                prompt=prompt,
                media_type=media_type,
                image_b64=image_b64,
                deadline=context.deadline,
            )

        return run_llm_step(
            role=self._role,
            label=self._label,
            name=self.name,
            prompt=self._prompt,
            inputs=inputs,
            context=context,
            control=control,
            text_invoke=text_invoke,
            vision_invoke=vision_invoke,
        )


__all__ = ["AnthropicAdapter"]
