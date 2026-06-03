"""Mapper ``AltoDocument → CanonicalLayout`` — pont format ALTO ↔ modèle neutre.

Première moitié du pont de la tranche segmentation (l'assembleur inverse
``layout → ALTO`` est un épaississement ultérieur). Le parsing reste en amont
(``parse_alto`` ; couche 2) ; ici on **projette** la structure ALTO vers le
vocabulaire neutre ``CanonicalLayout`` (couche 1) que consomment les métriques
de structure.

Choix de tranche (largeur minimale) : le texte de ligne est la **jointure simple**
des ``<String>`` (la dé-césure ``HypPart1/HypPart2`` est une affaire de projection
``layout → texte``, différée). Les ``id`` de région absents sont **synthétisés**
de façon déterministe (``region_<n>`` en ordre document) pour rester uniques et
appariables.
"""

from __future__ import annotations

from xerocr.domain.layout import (
    BBox,
    CanonicalLayout,
    Geometry,
    LayoutPage,
    Line,
    Region,
    Word,
)
from xerocr.formats._geometry import Point
from xerocr.formats.alto.types import (
    AltoBBox,
    AltoBlock,
    AltoComposedBlock,
    AltoDocument,
    AltoGraphicalElement,
    AltoIllustration,
    AltoLine,
    AltoPage,
    AltoString,
    AltoTextBlock,
)


class _Counter:
    """Compteur déterministe pour synthétiser les ``id`` de région manquants."""

    def __init__(self) -> None:
        self._n = 0

    def next_id(self) -> str:
        rid = f"region_{self._n}"
        self._n += 1
        return rid


def _geometry(
    bbox: AltoBBox | None, polygon: tuple[Point, ...] | None
) -> Geometry | None:
    if bbox is None and not polygon:
        return None
    neutral = (
        BBox(x=bbox.hpos, y=bbox.vpos, width=bbox.width, height=bbox.height)
        if bbox is not None
        else None
    )
    return Geometry(bbox=neutral, polygon=tuple(polygon or ()))


def _word(string: AltoString) -> Word:
    return Word(
        text=string.content,
        geometry=_geometry(string.bbox, None),
        confidence=string.confidence,
    )


def _line(line: AltoLine) -> Line:
    words = tuple(_word(s) for s in line.strings)
    return Line(
        id=line.id,
        text=" ".join(w.text for w in words),
        geometry=_geometry(line.bbox, line.polygon),
        baseline=tuple(line.baseline or ()),
        words=words,
    )


def _region(block: AltoBlock, counter: _Counter) -> Region:
    rid = block.id or counter.next_id()
    if isinstance(block, AltoTextBlock):
        return Region(
            id=rid,
            region_type=block.block_type or "text",
            geometry=_geometry(block.bbox, block.polygon),
            lines=tuple(_line(line) for line in block.lines),
        )
    if isinstance(block, AltoComposedBlock):
        return Region(
            id=rid,
            region_type=block.block_type or "composed",
            geometry=_geometry(block.bbox, block.polygon),
            regions=tuple(_region(child, counter) for child in block.blocks),
        )
    if isinstance(block, AltoIllustration):
        return Region(
            id=rid,
            region_type=block.block_type or "illustration",
            geometry=_geometry(block.bbox, block.polygon),
        )
    if isinstance(block, AltoGraphicalElement):
        return Region(
            id=rid,
            region_type="graphical",
            geometry=_geometry(block.bbox, block.polygon),
        )
    # Union fermée (discriminée par ``kind``) : aucune autre branche possible.
    raise AssertionError(f"bloc ALTO non géré : {block!r}")  # pragma: no cover


def _page(page: AltoPage, counter: _Counter) -> LayoutPage:
    regions = tuple(_region(block, counter) for block in page.blocks)
    return LayoutPage(
        width=page.width,
        height=page.height,
        regions=regions,
        reading_order=tuple(region.id for region in regions),
    )


def alto_to_layout(document: AltoDocument) -> CanonicalLayout:
    """Projette un ``AltoDocument`` parsé vers le ``CanonicalLayout`` neutre."""
    counter = _Counter()
    return CanonicalLayout(
        pages=tuple(_page(page, counter) for page in document.pages)
    )


__all__ = ["alto_to_layout"]
