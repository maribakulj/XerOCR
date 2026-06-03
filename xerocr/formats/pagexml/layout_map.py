"""Mapper ``PageDocument → CanonicalLayout`` — pont format PAGE ↔ modèle neutre.

Pendant de ``alto_to_layout`` pour PAGE XML (PRImA). Différences de convention
projetées vers le même vocabulaire neutre :

- géométrie en **polygones** (``Coords``) → ``Geometry.polygon`` (pas de bbox PAGE) ;
- niveau **ligne** sans mots (PAGE n'a pas de ``<String>``) → ``Line.text`` direct,
  ``Line.words = ()`` ;
- **ordre de lecture en arbre** (``ReadingOrder``) → liste plate via ``flatten()`` ;
- régions non-texte (``ImageRegion``…) → ``Region`` sans lignes, ``region_type``
  reprenant le label PRImA.

Les ``id`` de région absents sont synthétisés (``region_<n>``) comme côté ALTO.
"""

from __future__ import annotations

from xerocr.domain.layout import (
    CanonicalLayout,
    Geometry,
    LayoutPage,
    Line,
    Region,
)
from xerocr.formats._geometry import Point
from xerocr.formats.pagexml.types import (
    PageDocument,
    PageGenericRegion,
    PagePage,
    PageRegion,
    PageTextLine,
    PageTextRegion,
)


class _Counter:
    """Compteur déterministe pour les ``id`` de région manquants."""

    def __init__(self) -> None:
        self._n = 0

    def next_id(self) -> str:
        rid = f"region_{self._n}"
        self._n += 1
        return rid


def _geometry(coords: tuple[Point, ...] | None) -> Geometry | None:
    if not coords:
        return None
    return Geometry(polygon=coords)


def _line(line: PageTextLine) -> Line:
    return Line(
        id=line.id,
        text=line.text,
        geometry=_geometry(line.coords),
        baseline=tuple(line.baseline or ()),
        confidence=line.confidence,
    )


def _region(region: PageRegion, counter: _Counter) -> Region:
    rid = region.id or counter.next_id()
    if isinstance(region, PageTextRegion):
        return Region(
            id=rid,
            region_type=region.region_type or "text",
            geometry=_geometry(region.coords),
            lines=tuple(_line(line) for line in region.text_lines),
            regions=tuple(_region(child, counter) for child in region.regions),
        )
    if isinstance(region, PageGenericRegion):
        return Region(
            id=rid,
            region_type=region.region_type or region.region_name,
            geometry=_geometry(region.coords),
            regions=tuple(_region(child, counter) for child in region.regions),
        )
    raise AssertionError(f"région PAGE non gérée : {region!r}")  # pragma: no cover


def _page(page: PagePage, counter: _Counter) -> LayoutPage:
    regions = tuple(_region(region, counter) for region in page.regions)
    if page.reading_order is not None:
        reading_order = page.reading_order.flatten()
    else:
        reading_order = tuple(region.id for region in regions)
    return LayoutPage(
        width=page.image_width,
        height=page.image_height,
        regions=regions,
        reading_order=reading_order,
    )


def page_to_layout(document: PageDocument) -> CanonicalLayout:
    """Projette un ``PageDocument`` parsé vers le ``CanonicalLayout`` neutre."""
    counter = _Counter()
    return CanonicalLayout(
        pages=tuple(_page(page, counter) for page in document.pages)
    )


__all__ = ["page_to_layout"]
