"""Projecteurs (couche 3) — convertissent un artefact vers le type qu'une
métrique consomme, sous le contrôle déclaratif d'une ``ProjectionSpec``.

Socle : ``layout_to_text`` — projette un ``CanonicalLayout`` vers du texte brut
en **ordre de lecture** (régions ordonnées par ``reading_order``, sous-régions à
plat, lignes jointes). C'est ce qui permet de noter une sortie **structurée**
(ALTO/PAGE/LAYOUT) avec les métriques **texte** (CER/WER) contre une référence
texte — sans coupler la métrique au format.

Premier consommateur de ``ProjectionSpec`` (réserve §9 levée). Les projecteurs
sont **first-party** (non pluggables, cf. CLAUDE.md §3) : résolution par un
lookup builtin, pas un registre injecté.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping

from xerocr.domain.layout import CanonicalLayout, LayoutPage, Region
from xerocr.evaluation.errors import EvaluationError

#: Valeur de paramètre admissible (miroir de ``ProjectionSpec.params``).
ParamValue = str | int | float | bool

#: Un projecteur : ``(représentation source, params) → représentation cible``.
Projector = Callable[[object, Mapping[str, ParamValue]], object]


def _ordered_top_regions(page: LayoutPage) -> tuple[Region, ...]:
    """Régions de premier niveau dans l'ordre de lecture (sinon ordre déclaré)."""
    if not page.reading_order:
        return page.regions
    by_id = {region.id: region for region in page.regions}
    seen = set(page.reading_order)
    ordered = [by_id[rid] for rid in page.reading_order if rid in by_id]
    ordered.extend(region for region in page.regions if region.id not in seen)
    return tuple(ordered)


def _region_text(region: Region) -> str:
    """Texte d'une région : lignes puis sous-régions (profondeur d'abord)."""
    parts = [line.text for line in region.lines if line.text]
    for sub in region.regions:
        sub_text = _region_text(sub)
        if sub_text:
            parts.append(sub_text)
    return "\n".join(parts)


def layout_to_text(representation: object, params: Mapping[str, ParamValue]) -> object:
    """Projette un ``CanonicalLayout`` en texte brut, en ordre de lecture.

    Lignes jointes par ``\\n``, régions par ``\\n\\n``. Déterministe.
    """
    if not isinstance(representation, CanonicalLayout):
        raise EvaluationError(
            "layout_to_text : un CanonicalLayout est attendu, reçu "
            f"{type(representation).__name__}."
        )
    blocks: list[str] = []
    for page in representation.pages:
        for region in _ordered_top_regions(page):
            text = _region_text(region)
            if text:
                blocks.append(text)
    return "\n\n".join(blocks)


_BUILTIN: dict[str, Projector] = {"layout_to_text": layout_to_text}


def get_projector(name: str) -> Projector:
    """Résout un projecteur first-party par nom, ou lève ``EvaluationError``."""
    try:
        return _BUILTIN[name]
    except KeyError:
        raise EvaluationError(
            f"projecteur inconnu : {name!r} (disponibles : "
            f"{', '.join(sorted(_BUILTIN))})."
        ) from None


__all__ = ["Projector", "get_projector", "layout_to_text"]
