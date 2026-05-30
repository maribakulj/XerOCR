"""Parser ALTO tolérant (v2/v3/v4), via l'entonnoir ``safe_parse_xml``.

Extrait toute la structure mesurable : régions de tout type (TextBlock,
ComposedBlock récursif, Illustration, GraphicalElement), géométrie numérique
(bbox + polygone + baseline), confidence de mot. Les éléments non modélisés
(contenu de marge…) sont signalés par un ``warning``, jamais perdus en silence.
"""

from __future__ import annotations

import logging

from lxml import etree

from xerocr.domain.errors import FormatError
from xerocr.formats._geometry import Point, parse_points
from xerocr.formats._xml import safe_parse_xml
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

logger = logging.getLogger(__name__)

_MARGINS = {"TopMargin", "LeftMargin", "RightMargin", "BottomMargin"}
_BLOCK_NAMES = {"TextBlock", "ComposedBlock", "Illustration", "GraphicalElement"}


class AltoParseError(FormatError):
    """ALTO illisible (XML invalide, vide, DOCTYPE interdit, ou sans page)."""


def _lname(el: etree._Element) -> str:
    return etree.QName(el).localname if isinstance(el.tag, str) else ""


def _detect_version(tag: str) -> str | None:
    namespace = etree.QName(tag).namespace
    if namespace is None:
        return "none"
    for marker in ("ns-v2", "ns-v3", "ns-v4"):
        if marker in namespace:
            return marker.replace("ns-", "")
    return None


def _int_attr(el: etree._Element, name: str) -> int | None:
    raw = el.get(name)
    if raw is None:
        return None
    try:
        return int(float(raw))
    except ValueError:
        return None


def _bbox(el: etree._Element) -> AltoBBox | None:
    hpos = _int_attr(el, "HPOS")
    vpos = _int_attr(el, "VPOS")
    width = _int_attr(el, "WIDTH")
    height = _int_attr(el, "HEIGHT")
    if hpos is None or vpos is None or width is None or height is None:
        return None
    return AltoBBox(hpos=hpos, vpos=vpos, width=width, height=height)


def _points_attr(el: etree._Element, name: str) -> tuple[Point, ...] | None:
    raw = el.get(name)
    if raw is None:
        return None
    try:
        return parse_points(raw)
    except ValueError:
        logger.warning("[alto] %s illisible, géométrie ignorée : %r", name, raw)
        return None


def _polygon(el: etree._Element) -> tuple[Point, ...] | None:
    for shape in el:
        if _lname(shape) == "Shape":
            for poly in shape:
                if _lname(poly) == "Polygon":
                    return _points_attr(poly, "POINTS")
    return None


def _parse_string(el: etree._Element) -> AltoString:
    confidence: float | None = None
    wc = el.get("WC")
    if wc is not None:
        try:
            confidence = float(wc)
        except ValueError:
            confidence = None
    return AltoString(
        content=el.get("CONTENT", ""),
        id=el.get("ID"),
        bbox=_bbox(el),
        confidence=confidence,
        subs_type=el.get("SUBS_TYPE"),
        subs_content=el.get("SUBS_CONTENT"),
    )


def _parse_line(el: etree._Element) -> AltoLine:
    strings = tuple(_parse_string(c) for c in el if _lname(c) == "String")
    return AltoLine(
        id=el.get("ID"),
        bbox=_bbox(el),
        polygon=_polygon(el),
        baseline=_points_attr(el, "BASELINE"),
        strings=strings,
    )


def _parse_text_block(el: etree._Element) -> AltoTextBlock:
    lines = tuple(_parse_line(c) for c in el if _lname(c) == "TextLine")
    return AltoTextBlock(
        id=el.get("ID"),
        block_type=el.get("TYPE"),
        bbox=_bbox(el),
        polygon=_polygon(el),
        lines=lines,
    )


def _parse_composed(el: etree._Element) -> AltoComposedBlock:
    return AltoComposedBlock(
        id=el.get("ID"),
        block_type=el.get("TYPE"),
        bbox=_bbox(el),
        polygon=_polygon(el),
        blocks=_parse_blocks(el),
    )


def _parse_blocks(parent: etree._Element) -> tuple[AltoBlock, ...]:
    out: list[AltoBlock] = []
    for child in parent:
        name = _lname(child)
        if name == "TextBlock":
            out.append(_parse_text_block(child))
        elif name == "ComposedBlock":
            out.append(_parse_composed(child))
        elif name == "Illustration":
            out.append(
                AltoIllustration(
                    id=child.get("ID"),
                    block_type=child.get("TYPE"),
                    bbox=_bbox(child),
                    polygon=_polygon(child),
                )
            )
        elif name == "GraphicalElement":
            out.append(
                AltoGraphicalElement(
                    id=child.get("ID"),
                    bbox=_bbox(child),
                    polygon=_polygon(child),
                )
            )
    return tuple(out)


def _parse_page(el: etree._Element) -> AltoPage:
    print_space: etree._Element | None = None
    for child in el:
        name = _lname(child)
        if name == "PrintSpace":
            print_space = child
        elif name in _MARGINS and any(_lname(g) in _BLOCK_NAMES for g in child):
            logger.warning("[alto] contenu de %s non modélisé (ignoré)", name)
    container = print_space if print_space is not None else el
    return AltoPage(
        id=el.get("ID"),
        width=_int_attr(el, "WIDTH"),
        height=_int_attr(el, "HEIGHT"),
        blocks=_parse_blocks(container),
    )


def parse_alto(data: bytes) -> AltoDocument:
    """Parse des octets ALTO en ``AltoDocument`` (lève ``AltoParseError``)."""
    root = safe_parse_xml(data)
    if root is None:
        raise AltoParseError("ALTO illisible (XML invalide, vide ou DOCTYPE interdit).")

    version = _detect_version(root.tag) if isinstance(root.tag, str) else None

    measurement_unit: str | None = None
    for el in root.iter():
        if isinstance(el.tag, str) and _lname(el) == "MeasurementUnit":
            measurement_unit = (el.text or "").strip() or None
            break

    pages = tuple(
        _parse_page(el)
        for el in root.iter()
        if isinstance(el.tag, str) and _lname(el) == "Page"
    )
    return AltoDocument(
        pages=pages, source_version=version, measurement_unit=measurement_unit
    )


__all__ = ["parse_alto", "AltoParseError"]
