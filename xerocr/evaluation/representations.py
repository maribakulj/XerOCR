"""Chargement d'un artefact vers sa représentation comparable.

Le runner compare des **représentations** (``str`` pour le texte), pas des
artefacts bruts. T1 ne charge que le texte (``RAW_TEXT``/``CORRECTED_TEXT``) via
la couche 2 ; les autres types (``LAYOUT``…) arrivent avec leur tranche.
"""

from __future__ import annotations

from pathlib import Path

from xerocr.domain.artifacts import ArtifactType
from xerocr.domain.layout import CanonicalLayout
from xerocr.evaluation.errors import EvaluationError
from xerocr.formats.text import read_plaintext

_TEXT_TYPES = frozenset({ArtifactType.RAW_TEXT, ArtifactType.CORRECTED_TEXT})


def load_representation(uri: str, artifact_type: ArtifactType) -> object:
    """Charge le contenu pointé par ``uri`` dans sa représentation comparable."""
    try:
        data = Path(uri).read_bytes()
    except OSError as exc:
        raise EvaluationError(
            f"représentation illisible ({artifact_type.value}) : "
            f"{uri!r} ({exc})."
        ) from exc
    if artifact_type in _TEXT_TYPES:
        return read_plaintext(data)
    if artifact_type is ArtifactType.LAYOUT:
        try:
            return CanonicalLayout.model_validate_json(data)
        except ValueError as exc:
            raise EvaluationError(
                f"CanonicalLayout invalide ({uri!r}) : {exc}"
            ) from exc
    raise EvaluationError(
        f"représentation non chargeable pour le type {artifact_type.value!r}."
    )


__all__ = ["load_representation"]
