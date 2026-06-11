"""``MistralAdapter`` — post-correction LLM **et** transcription VLM (API Mistral).

Implémente le ``Module`` Protocol, trois modes (``PipelineMode``) selon le rôle :
``text_only`` (texte → corrigé), ``text_and_image`` (Pixtral : image + texte →
corrigé), ``zero_shot`` (Pixtral : image → texte). Clé ``MISTRAL_API_KEY`` ; SDK
``mistralai`` = **extra** importé paresseusement dans ``_invoke_mistral`` /
``_invoke_mistral_vision`` (isolés → **mockables**, CI sans clé ni réseau).
"""

from __future__ import annotations

from typing import Any

from xerocr.adapters.llm._base import (
    LLMCompletion,
    default_prompt_for_role,
    llm_input_types,
    llm_output_type,
    normalize_llm_content,
    run_llm_step,
    usage_tokens,
    validate_llm_label,
    validate_role,
)
from xerocr.domain.artifacts import Artifact, ArtifactType
from xerocr.domain.deadline import Deadline
from xerocr.domain.errors import AdapterStepError
from xerocr.domain.pipeline import PipelineMode
from xerocr.pipeline.protocols import ParamValue
from xerocr.pipeline.run_control import RunControl
from xerocr.pipeline.types import RunContext, StepOutput

_VERSION = "1.0"
_DEFAULT_MODEL = "mistral-small-latest"
_SUPPORTED: frozenset[str] = frozenset({"text_only", "text_and_image", "zero_shot"})


def _completion_from_chat(response: Any) -> LLMCompletion:
    """Réponse SDK ``chat.complete`` → ``LLMCompletion`` (texte + jetons).

    **Pur** (aucun réseau, aucun SDK) → la cartographie usage→jetons
    (``prompt_tokens``/``completion_tokens``) est **testable sur cassette** (étape
    2d) ; le client live (``# pragma: no cover``) ne le permettrait pas. Jetons →
    économie (coût cloud réel).
    """
    usage = getattr(response, "usage", None)
    tokens_in = usage_tokens(getattr(usage, "prompt_tokens", None))
    tokens_out = usage_tokens(getattr(usage, "completion_tokens", None))
    choices = getattr(response, "choices", None)
    if not choices:
        return LLMCompletion("", tokens_in, tokens_out)
    return LLMCompletion(
        normalize_llm_content(choices[0].message.content), tokens_in, tokens_out
    )


def _mistral_client(  # pragma: no cover -- réseau + clé API (cf. marqueur 'live')
    model: str, content: object, deadline: Deadline
) -> LLMCompletion:
    """Appel ``chat.complete`` partagé (texte ou multimodal)."""
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
        # Le SDK mistralai 1.x type strictement ses kwargs/messages ; on lui
        # passe des dicts valides à l'exécution (cf. tests live). ``ignore`` ciblé.
        client = Mistral(**client_kwargs)  # type: ignore[arg-type]
        response = client.chat.complete(
            model=model,
            messages=[{"role": "user", "content": content}],  # type: ignore[arg-type]
            temperature=0.0,
        )
    except Exception as exc:  # le SDK lève des erreurs HTTP/SDK variées
        raise AdapterStepError(
            f"mistral a échoué ({model}) : {type(exc).__name__}: {exc}"
        ) from exc
    return _completion_from_chat(response)


def _invoke_mistral(  # pragma: no cover -- réseau + clé API (cf. marqueur 'live')
    *, model: str, prompt: str, deadline: Deadline
) -> LLMCompletion:
    return _mistral_client(model, prompt, deadline)


def _invoke_mistral_vision(  # pragma: no cover -- réseau + clé API (cf. 'live')
    *, model: str, prompt: str, media_type: str, image_b64: str, deadline: Deadline
) -> LLMCompletion:
    content = [
        {"type": "text", "text": prompt},
        {"type": "image_url", "image_url": f"data:{media_type};base64,{image_b64}"},
    ]
    return _mistral_client(model, content, deadline)


class MistralAdapter:
    """Adapter Mistral multi-mode (post-correction texte/image, transcription VLM)."""

    def __init__(
        self,
        *,
        label: str,
        model: str = _DEFAULT_MODEL,
        role: str = "text_only",
        prompt: str | None = None,
    ) -> None:
        self._label = validate_llm_label(label, "MistralAdapter")
        self._model = model
        self._role: PipelineMode = validate_role(role, "MistralAdapter", _SUPPORTED)
        self._prompt = (
            prompt if prompt is not None else default_prompt_for_role(self._role)
        )

    @property
    def name(self) -> str:
        return f"mistral:{self._label}"

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
    ) -> StepOutput:
        def text_invoke(prompt: str) -> LLMCompletion:
            return _invoke_mistral(
                model=self._model, prompt=prompt, deadline=context.deadline
            )

        def vision_invoke(
            prompt: str, media_type: str, image_b64: str
        ) -> LLMCompletion:
            return _invoke_mistral_vision(
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


def list_mistral_models(*, timeout: float = 5.0) -> tuple[str, ...]:
    """IDs des modèles disponibles pour la clé Mistral courante (``models.list``).

    **Best-effort, commodité d'UI** : ``MISTRAL_API_KEY`` absente, SDK absent ou
    erreur réseau → ``()`` (l'interface retombe sur la saisie libre). Rien de
    hardcodé : la liste vient **directement de l'API Mistral**.
    """
    import os

    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        return ()
    try:
        from mistralai import Mistral  # type: ignore[import-not-found]
    except ImportError:
        return ()
    try:
        client = Mistral(api_key=api_key, timeout_ms=int(timeout * 1000))
        response = client.models.list()
    except Exception:  # noqa: BLE001 — commodité UI : ne jamais casser la page
        return ()
    data = getattr(response, "data", None) or ()
    ids = [m.id for m in data if isinstance(getattr(m, "id", None), str)]
    return tuple(sorted(set(ids)))


__all__ = ["MistralAdapter", "list_mistral_models"]
