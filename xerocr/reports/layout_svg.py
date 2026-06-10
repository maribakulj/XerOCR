"""Rendu **SVG serveur** d'un ``CanonicalLayout`` : régions → rectangles.

Couche 7 (reports) : transforme la géométrie neutre (domain) en SVG **autonome et
déterministe** — boîtes de régions + labels, sur un fond de page (ou l'image
source). Sert la visualisation de segmentation de la vitrine et reste
réutilisable par le rapport. **Aucun JS, aucun état** : même layout → mêmes octets
(invariant §12). On rend la **première page** (le squelette segmentation est
mono-page) ; les régions imbriquées sont aplaties (boîtes dessinées à plat).
"""

from __future__ import annotations

from collections.abc import Iterator
from html import escape

from xerocr.domain.layout import CanonicalLayout, LayoutPage, Region

#: Palette de contours de régions (cyclique, déterministe — pas d'aléa).
_STROKES = ("#3a6ea5", "#b5651d", "#4a7c59", "#7d5ba6", "#a63a4f")


def _flatten(regions: tuple[Region, ...]) -> Iterator[Region]:
    """Régions à plat (premier niveau puis imbriquées, profondeur d'abord)."""
    for region in regions:
        yield region
        yield from _flatten(region.regions)


def _page_size(page: LayoutPage) -> tuple[int, int]:
    """Dimensions de page déclarées, sinon l'enveloppe des boîtes de régions."""
    if page.width and page.height:
        return page.width, page.height
    width = height = 0
    for region in _flatten(page.regions):
        box = region.geometry.bbox if region.geometry else None
        if box is not None:
            width = max(width, box.x + box.width)
            height = max(height, box.y + box.height)
    return max(width, 1), max(height, 1)


def layout_to_svg(
    layout: CanonicalLayout, *, image_href: str | None = None, max_width: int = 720
) -> str:
    """Rend la 1ʳᵉ page d'un layout en SVG (boîtes de régions + labels).

    ``image_href`` (optionnel) place l'image source en fond ; sinon un fond de
    page neutre. ``max_width`` borne la largeur d'affichage (le ``viewBox`` garde
    les coordonnées réelles). Utilise des **attributs de présentation** SVG
    (``fill``/``stroke``), pas de ``style`` inline → compatible CSP stricte.
    """
    if not layout.pages:
        return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"></svg>'
    page = layout.pages[0]
    width, height = _page_size(page)
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {width} {height}" width="{min(width, max_width)}" '
        'role="img" class="seg-svg">'
    ]
    if image_href:
        parts.append(
            f'<image href="{escape(image_href, quote=True)}" x="0" y="0" '
            f'width="{width}" height="{height}"/>'
        )
    else:
        parts.append(
            f'<rect x="0" y="0" width="{width}" height="{height}" '
            'fill="#fafafa" stroke="#e6e6e6"/>'
        )
    for index, region in enumerate(_flatten(page.regions)):
        box = region.geometry.bbox if region.geometry else None
        if box is None:
            continue
        stroke = _STROKES[index % len(_STROKES)]
        label = escape(region.region_type or region.id)
        parts.append(
            f'<rect x="{box.x}" y="{box.y}" width="{box.width}" '
            f'height="{box.height}" fill="{stroke}" fill-opacity="0.08" '
            f'stroke="{stroke}" stroke-width="2"/>'
        )
        parts.append(
            f'<text x="{box.x + 4}" y="{box.y + 16}" font-size="13" '
            f'fill="{stroke}" font-family="monospace">{label}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


__all__ = ["layout_to_svg"]
