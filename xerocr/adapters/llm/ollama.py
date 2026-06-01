"""``OllamaAdapter`` — post-correction LLM via un serveur ollama local.

Deuxième famille LLM : prouve que le ``Module`` Protocol **généralise au-delà
d'openai** — même contrat ``RAW_TEXT`` → ``CORRECTED_TEXT``, sortie identique,
aucun cas particulier. Transport ``httpx`` (extra), importé paresseusement et
**isolé** dans ``_invoke_ollama`` (→ mockable, CI sans serveur).

C'est l'**implémentation de référence de l'annulation câblée** : ``_invoke_ollama``
enregistre ``client.close`` via ``RunControl.register_cancel_handle`` ; un
``trigger_cancel`` ferme la connexion et **interrompt la requête en vol**. La
distinction « annulation vs vraie panne réseau » se fait en sondant
``is_cancelled`` (``_fail_or_cancel``) — pas par une heuristique de message
fragile (dette de l'implémentation source, corrigée au portage).
"""

from __future__ import annotations

from typing import NoReturn

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
_DEFAULT_MODEL = "llama3"
_DEFAULT_HOST = "http://localhost:11434"


def _fail_or_cancel(control: RunControl, model: str, exc: Exception) -> NoReturn:
    """Traduit un échec d'appel ollama.

    Si l'annulation a été déclenchée, le ``client.close`` enregistré a fait
    échouer la requête en vol : on lève alors ``RunCancelledError`` (via
    ``raise_if_cancelled``). Sinon c'est une vraie panne → ``AdapterStepError``.
    Sonder ``is_cancelled`` est **fiable**, là où l'implémentation source
    devinait par le message d'exception (heuristique fragile, D-A).
    """
    control.raise_if_cancelled()
    raise AdapterStepError(f"ollama a échoué ({model}) : {exc}") from exc


def _invoke_ollama(  # pragma: no cover -- réseau (serveur ollama ; cf. marqueur 'live')
    *,
    model: str,
    prompt: str,
    host: str,
    deadline: Deadline,
    control: RunControl,
) -> str:
    try:
        import httpx  # type: ignore[import-not-found]
    except ImportError as exc:
        raise AdapterStepError(
            "ollama : httpx non installé (pip install 'xerocr[ollama]')."
        ) from exc
    payload = {"model": model, "prompt": prompt, "stream": False}
    client = httpx.Client(timeout=deadline.as_sdk_timeout())
    # Annulation câblée : fermer le client interrompt la requête en vol.
    control.register_cancel_handle(client.close)
    try:
        response = client.post(f"{host}/api/generate", json=payload)
        response.raise_for_status()
        data = response.json()
    except httpx.HTTPError as exc:
        _fail_or_cancel(control, model, exc)
    finally:
        client.close()
    return normalize_llm_content(data.get("response"))


class OllamaAdapter:
    """Post-correction LLM, serveur ollama local : ``RAW_TEXT`` → ``CORRECTED_TEXT``."""

    def __init__(
        self,
        *,
        label: str,
        model: str = _DEFAULT_MODEL,
        host: str = _DEFAULT_HOST,
        prompt: str = DEFAULT_CORRECTION_PROMPT,
    ) -> None:
        self._label = validate_llm_label(label, "OllamaAdapter")
        self._model = model
        self._host = host
        self._prompt = prompt

    @property
    def name(self) -> str:
        return f"ollama:{self._label}"

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
        corrected = _invoke_ollama(
            model=self._model,
            prompt=prompt,
            host=self._host,
            deadline=context.deadline,
            control=control,
        )
        return write_corrected(
            context.workspace_uri,
            context.document_id,
            self._label,
            self.name,
            corrected,
        )


__all__ = ["OllamaAdapter"]
