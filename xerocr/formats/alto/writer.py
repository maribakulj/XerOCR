"""Writer ALTO déterministe (lxml + canonicalisation C14N).

Sérialise un ``AltoDocument`` (construit par nous) en octets ALTO. Le C14N2 fixe
l'ordre des attributs et la forme des namespaces → sortie **déterministe** (cache
d'artefacts, round-trip). Aucun horodatage ni identifiant fabriqué n'est émis ;
construction sans état global (namespaces par élément) → thread-safe.

Garantie : ``parse_alto(write_alto(doc)) == doc`` pour un document dans la version
cible (``source_version`` reflète alors la version écrite).
"""

from __future__ import annotations

from lxml import etree

from xerocr.domain.errors import FormatError
from xerocr.formats._geometry import format_points
from xerocr.formats.alto.types import (
    AltoBBox,
    AltoBlock,
    AltoComposedBlock,
    AltoDocument,
    AltoIllustration,
    AltoLine,
    AltoPage,
    AltoString,
    AltoTextBlock,
)

_NS = {
    "v2": "http://www.loc.gov/standards/alto/ns-v2#",
    "v3": "http://www.loc.gov/standards/alto/ns-v3#",
    "v4": "http://www.loc.gov/standards/alto/ns-v4#",
}


class AltoWriteError(FormatError):
    """Version ALTO cible invalide."""


def _q(ns: str | None, local: str) -> str:
    return f"{{{ns}}}{local}" if ns else local


def _set_bbox(el: etree._Element, bbox: AltoBBox | None) -> None:
    if bbox is None:
        return
    el.set("HPOS", str(bbox.hpos))
    el.set("VPOS", str(bbox.vpos))
    el.set("WIDTH", str(bbox.width))
    el.set("HEIGHT", str(bbox.height))


def _write_polygon(
    parent: etree._Element, ns: str | None, polygon: tuple[tuple[int, int], ...] | None
) -> None:
    if polygon is None:
        return
    shape = etree.SubElement(parent, _q(ns, "Shape"))
    poly = etree.SubElement(shape, _q(ns, "Polygon"))
    poly.set("POINTS", format_points(polygon))


def _write_string(parent: etree._Element, ns: str | None, s: AltoString) -> None:
    el = etree.SubElement(parent, _q(ns, "String"))
    el.set("CONTENT", s.content)
    if s.id is not None:
        el.set("ID", s.id)
    if s.confidence is not None:
        el.set("WC", str(s.confidence))
    _set_bbox(el, s.bbox)
    if s.subs_type is not None:
        el.set("SUBS_TYPE", s.subs_type)
    if s.subs_content is not None:
        el.set("SUBS_CONTENT", s.subs_content)


def _write_line(parent: etree._Element, ns: str | None, line: AltoLine) -> None:
    el = etree.SubElement(parent, _q(ns, "TextLine"))
    if line.id is not None:
        el.set("ID", line.id)
    if line.baseline is not None:
        el.set("BASELINE", format_points(line.baseline))
    _set_bbox(el, line.bbox)
    _write_polygon(el, ns, line.polygon)
    for s in line.strings:
        _write_string(el, ns, s)


def _write_block(parent: etree._Element, ns: str | None, block: AltoBlock) -> None:
    if isinstance(block, AltoTextBlock):
        el = etree.SubElement(parent, _q(ns, "TextBlock"))
        if block.id is not None:
            el.set("ID", block.id)
        if block.block_type is not None:
            el.set("TYPE", block.block_type)
        _set_bbox(el, block.bbox)
        _write_polygon(el, ns, block.polygon)
        for line in block.lines:
            _write_line(el, ns, line)
    elif isinstance(block, AltoComposedBlock):
        el = etree.SubElement(parent, _q(ns, "ComposedBlock"))
        if block.id is not None:
            el.set("ID", block.id)
        if block.block_type is not None:
            el.set("TYPE", block.block_type)
        _set_bbox(el, block.bbox)
        _write_polygon(el, ns, block.polygon)
        for child in block.blocks:
            _write_block(el, ns, child)
    elif isinstance(block, AltoIllustration):
        el = etree.SubElement(parent, _q(ns, "Illustration"))
        if block.id is not None:
            el.set("ID", block.id)
        if block.block_type is not None:
            el.set("TYPE", block.block_type)
        _set_bbox(el, block.bbox)
        _write_polygon(el, ns, block.polygon)
    else:  # AltoGraphicalElement
        el = etree.SubElement(parent, _q(ns, "GraphicalElement"))
        if block.id is not None:
            el.set("ID", block.id)
        _set_bbox(el, block.bbox)
        _write_polygon(el, ns, block.polygon)


def _write_page(layout: etree._Element, ns: str | None, page: AltoPage) -> None:
    el = etree.SubElement(layout, _q(ns, "Page"))
    if page.id is not None:
        el.set("ID", page.id)
    if page.width is not None:
        el.set("WIDTH", str(page.width))
    if page.height is not None:
        el.set("HEIGHT", str(page.height))
    print_space = etree.SubElement(el, _q(ns, "PrintSpace"))
    for block in page.blocks:
        _write_block(print_space, ns, block)


def write_alto(document: AltoDocument, *, version: str = "v4") -> bytes:
    """Sérialise un ``AltoDocument`` en octets ALTO canoniques (C14N2)."""
    if version != "none" and version not in _NS:
        raise AltoWriteError(
            f"version ALTO invalide : {version!r} (attendu v2/v3/v4/none)."
        )
    ns = _NS.get(version)
    nsmap = {None: ns} if ns else None
    root = etree.Element(_q(ns, "alto"), nsmap=nsmap)  # type: ignore[arg-type]
    if document.measurement_unit is not None:
        description = etree.SubElement(root, _q(ns, "Description"))
        unit = etree.SubElement(description, _q(ns, "MeasurementUnit"))
        unit.text = document.measurement_unit
    layout = etree.SubElement(root, _q(ns, "Layout"))
    for page in document.pages:
        _write_page(layout, ns, page)
    return etree.tostring(root, method="c14n2")


__all__ = ["write_alto", "AltoWriteError"]
