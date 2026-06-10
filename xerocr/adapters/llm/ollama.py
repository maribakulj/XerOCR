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
    LLMCompletion,
    normalize_llm_content,
    run_llm_step,
    usage_tokens,
    validate_llm_label,
)
from xerocr.domain.artifacts import Artifact, ArtifactType
from xerocr.domain.deadline import Deadline
from xerocr.domain.errors import AdapterStepError
from xerocr.pipeline.protocols import ParamValue
from xerocr.pipeline.run_control import RunControl
from xerocr.pipeline.types import RunContext, StepOutput

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
) -> LLMCompletion:
    try:
        import httpx  # type: ignore[import-not-found]
    except ImportError as exc:
        raise AdapterStepError(
            "ollama : httpx non installé (pip install 'xerocr[ollama]')."
        ) from exc
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
    }
    client = httpx.Client(timeout=deadline.as_sdk_timeout())
    # Annulation câblée : fermer le client interrompt la requête en vol.
    control.register_cancel_handle(client.close)
    try:
        # **/api/chat** (et non /api/generate) : applique le gabarit de chat du
        # modèle. Indispensable pour les modèles *instruct* (ex. churro), qui
        # échouent sur /api/generate (complétion brute). C'est l'endpoint
        # qu'utilise ``ollama run``.
        response = client.post(f"{host}/api/chat", json=payload)
        response.raise_for_status()
        data = response.json()
    except httpx.HTTPError as exc:
        _fail_or_cancel(control, model, exc)
    finally:
        client.close()
    # Ollama peut renvoyer une **erreur en HTTP 200** (modèle introuvable sous ce
    # nom, mémoire insuffisante…) : ``raise_for_status`` ne la voit pas. On la
    # remonte explicitement, sinon la « correction » serait un texte vide silencieux.
    if isinstance(data, dict) and data.get("error"):
        raise AdapterStepError(f"ollama a échoué ({model}) : {data['error']}")
    message = data.get("message") if isinstance(data, dict) else None
    content = message.get("content") if isinstance(message, dict) else None
    # /api/chat expose la consommation : prompt_eval_count / eval_count.
    counts = data if isinstance(data, dict) else {}
    return LLMCompletion(
        normalize_llm_content(content),
        usage_tokens(counts.get("prompt_eval_count")),
        usage_tokens(counts.get("eval_count")),
    )


def list_installed_models(
    host: str = _DEFAULT_HOST, *, timeout: float = 3.0
) -> tuple[str, ...]:
    """Noms des modèles installés sur le serveur ollama (``GET /api/tags``).

    **Best-effort, commodité d'UI** : serveur injoignable, ``httpx`` absent ou
    réponse inattendue → ``()`` (l'interface retombe alors sur la saisie libre).
    Aucune exception propagée. Le ``name`` renvoyé est le **tag exact** servable à
    ``/api/generate`` (ex. ``gemma3:1b`` ou ``hf.co/…/churro-3B-GGUF:Q4_K_M``).
    """
    try:
        import httpx  # type: ignore[import-not-found]
    except ImportError:
        return ()
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(f"{host}/api/tags")
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPError, ValueError):
        return ()
    models = data.get("models") if isinstance(data, dict) else None
    if not isinstance(models, list):
        return ()
    return tuple(
        m["name"]
        for m in models
        if isinstance(m, dict) and isinstance(m.get("name"), str)
    )


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
    ) -> StepOutput:
        def text_invoke(prompt: str) -> LLMCompletion:
            return _invoke_ollama(
                model=self._model,
                prompt=prompt,
                host=self._host,
                deadline=context.deadline,
                control=control,
            )

        return run_llm_step(
            role="text_only",
            label=self._label,
            name=self.name,
            prompt=self._prompt,
            inputs=inputs,
            context=context,
            control=control,
            text_invoke=text_invoke,
            vision_invoke=None,
        )


__all__ = ["OllamaAdapter"]
