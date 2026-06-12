"""Chargement d'un artefact vers sa représentation comparable.

Le runner compare des **représentations** (``str`` pour le texte), pas des
artefacts bruts. Charge aujourd'hui le texte (``RAW_TEXT``/``CORRECTED_TEXT``) via
la couche 2 ; les autres types (``LAYOUT``…) arrivent avec leur tranche.
"""

from __future__ import annotations

from pathlib import Path

from xerocr.domain.artifacts import ArtifactType
from xerocr.domain.errors import FormatError
from xerocr.domain.evaluation import EvaluationView
from xerocr.domain.layout import CanonicalLayout
from xerocr.evaluation.errors import EvaluationError
from xerocr.formats.alto import parse_alto
from xerocr.formats.alto.layout_map import alto_to_layout
from xerocr.formats.pagexml import parse_pagexml
from xerocr.formats.pagexml.layout_map import page_to_layout
from xerocr.formats.text import get_builtin_profile, read_plaintext

_TEXT_TYPES = frozenset(
    {
        ArtifactType.RAW_TEXT,
        ArtifactType.CORRECTED_TEXT,
        ArtifactType.REFERENCE_TEXT,
    }
)


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
        return _load_layout(uri, data)
    raise EvaluationError(
        f"représentation non chargeable pour le type {artifact_type.value!r}."
    )


def _load_layout(uri: str, data: bytes) -> CanonicalLayout:
    """Charge un ``CanonicalLayout`` depuis du JSON natif, de l'ALTO ou du PAGE.

    XML (premier octet non-blanc ``<``) → ALTO ou PAGE selon le marqueur de
    racine (``PcGts``/``pagecontent`` = PAGE, sinon ALTO) ; autrement JSON
    sérialisé d'un ``CanonicalLayout``.
    """
    if data.lstrip()[:1] == b"<":
        head = data[:4096].lower()
        is_page = b"pcgts" in head or b"pagecontent" in head
        try:
            if is_page:
                return page_to_layout(parse_pagexml(data))
            return alto_to_layout(parse_alto(data))
        except (ValueError, FormatError) as exc:
            kind = "PAGE" if is_page else "ALTO"
            raise EvaluationError(
                f"{kind} illisible en layout ({uri!r}) : {exc}"
            ) from exc
    try:
        return CanonicalLayout.model_validate_json(data)
    except ValueError as exc:
        raise EvaluationError(f"CanonicalLayout invalide ({uri!r}) : {exc}") from exc


def prepare_text(text: str, view: EvaluationView) -> str:
    """Applique la normalisation de la vue (profil + ``char_exclude``) à un texte.

    **La** définition de « préparé comme au scoring » : le runner et les
    analyses qui chargent leurs propres textes (bilan de correction) passent
    par ici — une seule implémentation, symétrique GT/hypothèse.
    """
    if view.normalization_profile is not None:
        try:
            profile = get_builtin_profile(view.normalization_profile)
        except KeyError as exc:
            raise EvaluationError(str(exc)) from exc
        text = profile.normalize(text)
    if view.char_exclude:
        excluded = set(view.char_exclude)
        text = "".join(char for char in text if char not in excluded)
    return text


__all__ = ["load_representation", "prepare_text"]
