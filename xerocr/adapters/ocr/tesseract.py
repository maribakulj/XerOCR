"""``TesseractAdapter`` — moteur OCR réel (Tesseract 5 via ``pytesseract``).

Implémente le ``Module`` Protocol (couche 4) **directement**. L'OCR a lieu dans
le binaire C ``tesseract`` lancé en sous-processus (le thread relâche le GIL).
``pytesseract`` est un **extra optionnel** (``xerocr[tesseract]``), importé
**paresseusement** dans ``_invoke_tesseract`` : importer ce module ne requiert ni
la lib ni le binaire — seule l'exécution les exige.

Sécurité : ``lang`` est validé (anti-injection ligne de commande) ; ``timeout``
est borné par la ``Deadline`` (un sous-processus figé ne doit pas geler le run).
Confidences et ALTO natif sont **différés** (pas de consommateur en T2).
"""

from __future__ import annotations

import re
from pathlib import Path

from xerocr.domain.artifacts import Artifact, ArtifactType, compute_content_hash
from xerocr.domain.errors import AdapterStepError
from xerocr.pipeline.protocols import ParamValue
from xerocr.pipeline.run_control import RunControl
from xerocr.pipeline.types import RunContext

_VERSION = "1.0"
_DEFAULT_TIMEOUT = 120.0

#: Codes langue Tesseract : ISO 639-3 (≥3 lettres ASCII), combinables par ``+``
#: (``fra+lat``). ``lang`` finit sur la ligne de commande tesseract → on refuse
#: tout caractère interprétable comme flag/séparateur (anti-injection).
_LANG_RE = re.compile(r"^[a-zA-Z]{3,}(?:\+[a-zA-Z]{3,})*$")


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
    ) -> dict[ArtifactType, Artifact]:
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
        output_path = (
            Path(context.workspace_uri)
            / f"{context.document_id.replace('/', '_')}.{self._label}.txt"
        )
        output_path.write_text(text, encoding="utf-8")
        return {
            ArtifactType.RAW_TEXT: Artifact(
                id=f"{context.document_id}:{self.name}:raw_text",
                document_id=context.document_id,
                type=ArtifactType.RAW_TEXT,
                uri=str(output_path),
                content_hash=compute_content_hash(text.encode("utf-8")),
            )
        }


__all__ = ["TesseractAdapter"]
