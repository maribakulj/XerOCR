"""Writer PAGE XML déterministe (lxml + C14N2). Symétrique du writer ALTO.

Garantie : ``parse_pagexml(write_pagexml(doc)) == doc`` pour un document dont le
``source_namespace`` est celui écrit. Sans état global → thread-safe ; zéro
horodatage (pas de ``Metadata``) → déterministe.
"""

from __future__ import annotations

from lxml import etree

from xerocr.domain.errors import FormatError
from xerocr.formats._geometry import format_points
from xerocr.formats.pagexml.types import (
    PageDocument,
    PagePage,
    PageRegion,
    PageTextLine,
    PageTextRegion,
    ReadingOrderGroup,
    ReadingOrderRef,
)

DEFAULT_PAGE_NS = "http://schema.primaresearch.org/PAGE/gts/pagecontent/2019-07-15"


class PageWriteError(FormatError):
    """Écriture PAGE impossible."""


def _q(ns: str, local: str) -> str:
    return f"{{{ns}}}{local}"


def _write_coords(
    parent: etree._Element, ns: str, points: tuple[tuple[int, int], ...]
) -> None:
    etree.SubElement(parent, _q(ns, "Coords")).set("points", format_points(points))


def _write_line(parent: etree._Element, ns: str, line: PageTextLine) -> None:
    el = etree.SubElement(parent, _q(ns, "TextLine"))
    if line.id is not None:
        el.set("id", line.id)
    if line.coords is not None:
        _write_coords(el, ns, line.coords)
    if line.baseline is not None:
        baseline = etree.SubElement(el, _q(ns, "Baseline"))
        baseline.set("points", format_points(line.baseline))
    text_equiv = etree.SubElement(el, _q(ns, "TextEquiv"))
    text_equiv.set("index", "0")
    if line.confidence is not None:
        text_equiv.set("conf", str(line.confidence))
    etree.SubElement(text_equiv, _q(ns, "Unicode")).text = line.text


def _write_region(parent: etree._Element, ns: str, region: PageRegion) -> None:
    if isinstance(region, PageTextRegion):
        el = etree.SubElement(parent, _q(ns, "TextRegion"))
        if region.id is not None:
            el.set("id", region.id)
        if region.region_type is not None:
            el.set("type", region.region_type)
        if region.coords is not None:
            _write_coords(el, ns, region.coords)
        for line in region.text_lines:
            _write_line(el, ns, line)
        for child in region.regions:
            _write_region(el, ns, child)
    else:  # PageGenericRegion
        el = etree.SubElement(parent, _q(ns, region.region_name))
        if region.id is not None:
            el.set("id", region.id)
        if region.region_type is not None:
            el.set("type", region.region_type)
        if region.coords is not None:
            _write_coords(el, ns, region.coords)
        for child in region.regions:
            _write_region(el, ns, child)


def _write_group(
    parent: etree._Element, ns: str, group: ReadingOrderGroup, index: int | None
) -> None:
    suffix = "Indexed" if index is not None else ""
    name = ("OrderedGroup" if group.ordered else "UnorderedGroup") + suffix
    el = etree.SubElement(parent, _q(ns, name))
    if index is not None:
        el.set("index", str(index))
    if group.id is not None:
        el.set("id", group.id)
    for position, child in enumerate(group.children):
        child_index = position if group.ordered else None
        if isinstance(child, ReadingOrderRef):
            ref_name = "RegionRefIndexed" if group.ordered else "RegionRef"
            ref_el = etree.SubElement(el, _q(ns, ref_name))
            if child_index is not None:
                ref_el.set("index", str(child_index))
            ref_el.set("regionRef", child.region_ref)
        else:
            _write_group(el, ns, child, child_index)


def _write_page(parent: etree._Element, ns: str, page: PagePage) -> None:
    el = etree.SubElement(parent, _q(ns, "Page"))
    if page.image_filename is not None:
        el.set("imageFilename", page.image_filename)
    if page.image_width is not None:
        el.set("imageWidth", str(page.image_width))
    if page.image_height is not None:
        el.set("imageHeight", str(page.image_height))
    if page.reading_order is not None:
        order_el = etree.SubElement(el, _q(ns, "ReadingOrder"))
        _write_group(order_el, ns, page.reading_order, None)
    for region in page.regions:
        _write_region(el, ns, region)


def write_pagexml(document: PageDocument, *, namespace: str | None = None) -> bytes:
    """Sérialise un ``PageDocument`` en octets PAGE XML canoniques (C14N2)."""
    ns = namespace or document.source_namespace or DEFAULT_PAGE_NS
    nsmap = {None: ns}
    root = etree.Element(_q(ns, "PcGts"), nsmap=nsmap)  # type: ignore[arg-type]
    for page in document.pages:
        _write_page(root, ns, page)
    return etree.tostring(root, method="c14n2")


__all__ = ["write_pagexml", "PageWriteError", "DEFAULT_PAGE_NS"]
