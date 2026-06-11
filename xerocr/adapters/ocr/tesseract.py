"""``TesseractAdapter`` — moteur OCR réel (Tesseract 5 via ``pytesseract``).

Implémente le ``Module`` Protocol (couche 4) **directement**. L'OCR a lieu dans
le binaire C ``tesseract`` lancé en sous-processus (le thread relâche le GIL).
``pytesseract`` est un **extra optionnel** (``xerocr[tesseract]``), importé
**paresseusement** dans ``_invoke_tesseract`` : importer ce module ne requiert ni
la lib ni le binaire — seule l'exécution les exige.

Sécurité : ``lang`` est validé (anti-injection ligne de commande) ; ``timeout``
est borné par la ``Deadline`` (un sous-processus figé ne doit pas geler le run).
Les **confidences** par mot (TSV natif, 0-100 → [0,1]) sont écrites en
sidecar JSON (``ConfidenceToken``) et publiées comme artefact ``CONFIDENCES``
— best-effort : un échec d'extraction dégrade en sidecar vide, jamais en
panne de l'OCR. ALTO natif reste différé (pas de consommateur).
"""

from __future__ import annotations

import json
import logging
import re
import subprocess
from collections.abc import Callable

from xerocr.adapters._workspace import workspace_artifact_path
from xerocr.domain.artifacts import Artifact, ArtifactType, compute_content_hash
from xerocr.domain.confidence import ConfidenceToken
from xerocr.domain.errors import AdapterStepError
from xerocr.pipeline.protocols import ParamValue
from xerocr.pipeline.run_control import RunControl
from xerocr.pipeline.types import RunContext, StepOutput

logger = logging.getLogger(__name__)

_VERSION = "1.0"
_DEFAULT_TIMEOUT = 120.0

#: Codes langue Tesseract : ISO 639-3 (≥3 lettres ASCII), combinables par ``+``
#: (``fra+lat``). ``lang`` finit sur la ligne de commande tesseract → on refuse
#: tout caractère interprétable comme flag/séparateur (anti-injection).
_LANG_RE = re.compile(r"^[a-zA-Z]{3,}(?:\+[a-zA-Z]{3,})*$")

#: Lanceur de sous-processus, injectable → version sondable en test sans binaire.
BinaryRunner = Callable[..., "subprocess.CompletedProcess[str]"]


def tesseract_binary_version(*, run: BinaryRunner = subprocess.run) -> str | None:
    """Version du binaire ``tesseract`` (1ʳᵉ ligne de ``tesseract --version``).

    **Best-effort, jamais bloquant** : binaire absent, timeout, ou sortie illisible
    → ``None`` (jamais une panne). Sert la **reproductibilité** (``RunManifest`` §12) :
    deux runs ne sont comparables qu'à version de binaire égale — la version
    d'*adapter* (``_VERSION``) ne dit rien du Tesseract réellement installé.
    ``run`` est injecté → la sonde est déterministe en test, sans le binaire.

    Tesseract émet sa bannière tantôt sur ``stdout`` tantôt sur ``stderr`` selon le
    build → on lit les deux et garde la 1ʳᵉ ligne non vide (ex. ``tesseract 5.3.0``).
    """
    try:
        completed = run(
            ["tesseract", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    lines = ((completed.stdout or "") + "\n" + (completed.stderr or "")).splitlines()
    for line in lines:
        if line.strip():
            return line.strip()
    return None


def _invoke_tesseract(  # pragma: no cover -- binaire requis (cf. marqueur 'live')
    *, image_path: str, lang: str, psm: int, oem: int, timeout: float
) -> str:
    """Lance tesseract et renvoie le texte. **Isolé → mockable** (CI sans binaire)."""
    try:
        import pytesseract  # type: ignore[import-not-found]
    except ImportError as exc:
        raise AdapterStepError(
            "tesseract : pytesseract non installé "
            "(pip install 'xerocr[tesseract]' + binaire tesseract)."
        ) from exc
    config = f"--oem {oem} --psm {psm}"
    try:
        text = pytesseract.image_to_string(
            image_path, lang=lang, config=config, timeout=timeout
        )
    except (
        pytesseract.TesseractNotFoundError,
        pytesseract.TesseractError,
        RuntimeError,
    ) as exc:
        raise AdapterStepError(
            f"tesseract a échoué sur {image_path!r} : {type(exc).__name__}: {exc}"
        ) from exc
    return str(text).strip()


def _invoke_tesseract_confidences(  # pragma: no cover -- binaire requis ('live')
    *, image_path: str, lang: str, psm: int, oem: int, timeout: float
) -> list[ConfidenceToken]:
    """Confidences par mot via ``image_to_data`` (TSV natif, conf 0-100)."""
    import pytesseract  # type: ignore[import-not-found]

    data = pytesseract.image_to_data(
        image_path,
        lang=lang,
        config=f"--psm {psm} --oem {oem}",
        timeout=timeout,
        output_type=pytesseract.Output.DICT,
    )
    tokens: list[ConfidenceToken] = []
    for word, conf in zip(data["text"], data["conf"], strict=False):
        if not isinstance(word, str) or not word.strip():
            continue
        value = float(conf)
        if value < 0:  # -1 : entrée non textuelle du TSV
            continue
        tokens.append(
            ConfidenceToken(text=word.strip(), confidence=min(value / 100.0, 1.0))
        )
    return tokens


class TesseractAdapter:
    """OCR Tesseract 5 ; écrit le texte dans le workspace, renvoie un ``RAW_TEXT``."""

    def __init__(
        self, *, label: str, lang: str = "fra", psm: int = 6, oem: int = 3
    ) -> None:
        if not label or not all(c.isalnum() or c in "_-" for c in label):
            raise AdapterStepError(
                f"TesseractAdapter : label invalide {label!r} "
                "(alphanumérique + _ - uniquement)."
            )
        if not _LANG_RE.fullmatch(lang):
            raise AdapterStepError(
                f"TesseractAdapter : lang invalide {lang!r} "
                "(ISO 639-3, combinable par '+' : ex. 'fra+lat')."
            )
        if not 0 <= psm <= 13:
            raise AdapterStepError(f"TesseractAdapter : psm ∈ [0, 13], reçu {psm}.")
        if not 0 <= oem <= 3:
            raise AdapterStepError(f"TesseractAdapter : oem ∈ [0, 3], reçu {oem}.")
        self._label = label
        self._lang = lang
        self._psm = psm
        self._oem = oem

    @property
    def name(self) -> str:
        return f"tesseract:{self._label}"

    @property
    def version(self) -> str:
        return _VERSION

    def system_binaries(self) -> dict[str, str]:
        """Version du **binaire externe** pour le ``RunManifest`` (reproductibilité).

        Hook de **provenance optionnel** (hors ``Module`` Protocol, qui reste le
        contrat d'exécution unique) : l'orchestrateur l'appelle par *duck-typing*
        sur les modules qui l'exposent et fusionne le résultat dans
        ``system_binaries_lock``. Best-effort : binaire absent → ``{}``.
        """
        version = tesseract_binary_version()
        return {"tesseract": version} if version is not None else {}

    @property
    def input_types(self) -> frozenset[ArtifactType]:
        return frozenset({ArtifactType.IMAGE})

    @property
    def output_types(self) -> frozenset[ArtifactType]:
        return frozenset({ArtifactType.RAW_TEXT, ArtifactType.CONFIDENCES})

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
            raise AdapterStepError(
                f"{self.name} : workspace requis (RunContext.workspace_uri)."
            )
        timeout = max(0.001, context.deadline.clamp_to_remaining(_DEFAULT_TIMEOUT))
        text = _invoke_tesseract(
            image_path=image.uri,
            lang=self._lang,
            psm=self._psm,
            oem=self._oem,
            timeout=timeout,
        )
        output_path = workspace_artifact_path(
            context.workspace_uri, context.document_id, self._label, "txt"
        )
        output_path.write_text(text, encoding="utf-8")
        # Confidences best-effort : un échec d'extraction ne doit pas faire
        # échouer un OCR réussi — sidecar vide + avertissement.
        try:
            tokens = _invoke_tesseract_confidences(
                image_path=image.uri,
                lang=self._lang,
                psm=self._psm,
                oem=self._oem,
                timeout=timeout,
            )
        except (
            AdapterStepError,
            ImportError,
            RuntimeError,
            ValueError,
            OSError,
        ) as exc:
            logger.warning(
                "[tesseract] confidences dégradées (sidecar vide) : %s", exc
            )
            tokens = []
        sidecar = json.dumps(
            [token.model_dump() for token in tokens], ensure_ascii=False
        ).encode("utf-8")
        sidecar_path = workspace_artifact_path(
            context.workspace_uri,
            context.document_id,
            self._label,
            "confidences.json",
        )
        sidecar_path.write_bytes(sidecar)
        return StepOutput(
            artifacts={
                ArtifactType.RAW_TEXT: Artifact(
                    id=f"{context.document_id}:{self.name}:raw_text",
                    document_id=context.document_id,
                    type=ArtifactType.RAW_TEXT,
                    uri=str(output_path),
                    content_hash=compute_content_hash(text.encode("utf-8")),
                ),
                ArtifactType.CONFIDENCES: Artifact(
                    id=f"{context.document_id}:{self.name}:confidences",
                    document_id=context.document_id,
                    type=ArtifactType.CONFIDENCES,
                    uri=str(sidecar_path),
                    content_hash=compute_content_hash(sidecar),
                ),
            }
        )


__all__ = ["TesseractAdapter", "tesseract_binary_version"]
