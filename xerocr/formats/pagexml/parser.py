"""Parser PAGE XML tolérant (millésimes PRImA variés), via ``safe_parse_xml``.

Extrait : régions de tout type (TextRegion + génériques non-texte), imbriquées ;
géométrie en polygones (``Coords``) + ``Baseline`` ; texte de ligne via le
``TextEquiv`` d'``index`` le plus bas ; arbre d'ordre de lecture.
"""

from __future__ import annotations

import logging

from lxml import etree

from xerocr.domain.errors import FormatError
from xerocr.formats._geometry import Point, parse_points
from xerocr.formats._xml import safe_parse_xml
from xerocr.formats.pagexml.types import (
    PageDocument,
    PageGenericRegion,
    PagePage,
    PageRegion,
    PageTextLine,
    PageTextRegion,
    ReadingOrderGroup,
    ReadingOrderNode,
    ReadingOrderRef,
)

logger = logging.getLogger(__name__)


class PageParseError(FormatError):
    """PAGE XML illisible (XML invalide, vide, DOCTYPE interdit, ou sans page)."""


def _lname(el: etree._Element) -> str:
    return etree.QName(el).localname if isinstance(el.tag, str) else ""


def _int_attr(el: etree._Element, name: str) -> int | None:
    raw = el.get(name)
    if raw is None:
        return None
    try:
        return int(float(raw))
    except ValueError:
        return None


def _points_child(el: etree._Element, child_name: str) -> tuple[Point, ...] | None:
    for child in el:
        if _lname(child) == child_name:
            raw = child.get("points")
            if raw is None:
                return None
            try:
                return parse_points(raw)
            except ValueError:
                logger.warning(
                    "[page] %s illisible, géométrie ignorée : %r", child_name, raw
                )
                return None
    return None


def _textequiv_text_conf(te: etree._Element) -> tuple[str, float | None]:
    unicode_text = ""
    for node in te:
        if _lname(node) == "Unicode":
            unicode_text = node.text or ""
            break
    conf: float | None = None
    raw_conf = te.get("conf")
    if raw_conf is not None:
        try:
            conf = float(raw_conf)
        except ValueError:
            conf = None
    return unicode_text, conf


def _line_text_and_conf(line: etree._Element) -> tuple[str, float | None]:
    """Texte + confidence de la ligne.

    On retient le ``TextEquiv`` de niveau ligne d'``index`` le plus bas. À défaut
    (lignes uniquement segmentées en mots, ex. certains exports Transkribus), on
    reconstruit le texte depuis les ``<Word>``.
    """
    best: tuple[int, str, float | None] | None = None
    for te in line:
        if _lname(te) != "TextEquiv":
            continue
        index = _int_attr(te, "index")
        order = index if index is not None else 0
        text, conf = _textequiv_text_conf(te)
        if best is None or order < best[0]:
            best = (order, text, conf)
    if best is not None:
        return best[1], best[2]

    words: list[str] = []
    for word in line:
        if _lname(word) != "Word":
            continue
        for te in word:
            if _lname(te) == "TextEquiv":
                words.append(_textequiv_text_conf(te)[0])
                break
    if words:
        return " ".join(words), None
    return "", None


def _parse_text_line(el: etree._Element) -> PageTextLine:
    text, conf = _line_text_and_conf(el)
    return PageTextLine(
        id=el.get("id"),
        coords=_points_child(el, "Coords"),
        baseline=_points_child(el, "Baseline"),
        text=text,
        confidence=conf,
    )


def _parse_text_region(el: etree._Element) -> PageTextRegion:
    lines = tuple(_parse_text_line(c) for c in el if _lname(c) == "TextLine")
    return PageTextRegion(
        id=el.get("id"),
        region_type=el.get("type"),
        coords=_points_child(el, "Coords"),
        text_lines=lines,
        regions=_parse_regions(el),
    )


def _parse_generic_region(el: etree._Element) -> PageGenericRegion:
    return PageGenericRegion(
        region_name=_lname(el),
        id=el.get("id"),
        region_type=el.get("type"),
        coords=_points_child(el, "Coords"),
        regions=_parse_regions(el),
    )


def _parse_regions(parent: etree._Element) -> tuple[PageRegion, ...]:
    out: list[PageRegion] = []
    for child in parent:
        name = _lname(child)
        if name == "TextRegion":
            out.append(_parse_text_region(child))
        elif name.endswith("Region"):
            out.append(_parse_generic_region(child))
    return tuple(out)


def _parse_group(el: etree._Element) -> ReadingOrderGroup:
    ordered = _lname(el).startswith("Ordered")
    indexed: list[tuple[int, ReadingOrderNode]] = []
    plain: list[ReadingOrderNode] = []
    for child in el:
        name = _lname(child)
        node: ReadingOrderNode | None = None
        if name in ("RegionRefIndexed", "RegionRef"):
            ref = child.get("regionRef")
            if ref is not None:
                node = ReadingOrderRef(region_ref=ref)
        elif name.startswith(("Ordered", "Unordered")):
            node = _parse_group(child)
        if node is None:
            continue
        index = _int_attr(child, "index")
        if index is not None:
            indexed.append((index, node))
        else:
            plain.append(node)
    children = [node for _, node in sorted(indexed, key=lambda pair: pair[0])] + plain
    return ReadingOrderGroup(id=el.get("id"), ordered=ordered, children=tuple(children))


def _parse_reading_order(page: etree._Element) -> ReadingOrderGroup | None:
    for child in page:
        if _lname(child) == "ReadingOrder":
            for group in child:
                if _lname(group).startswith(("Ordered", "Unordered")):
                    return _parse_group(group)
    return None


def _parse_page(el: etree._Element) -> PagePage:
    return PagePage(
        image_filename=el.get("imageFilename"),
        image_width=_int_attr(el, "imageWidth"),
        image_height=_int_attr(el, "imageHeight"),
        reading_order=_parse_reading_order(el),
        regions=_parse_regions(el),
    )


def parse_pagexml(data: bytes) -> PageDocument:
    """Parse des octets PAGE XML en ``PageDocument`` (lève ``PageParseError``)."""
    root = safe_parse_xml(data)
    if root is None:
        raise PageParseError("PAGE illisible (XML invalide, vide ou DOCTYPE interdit).")
    namespace = etree.QName(root).namespace if isinstance(root.tag, str) else None
    pages = tuple(
        _parse_page(el)
        for el in root.iter()
        if isinstance(el.tag, str) and _lname(el) == "Page"
    )
    return PageDocument(pages=pages, source_namespace=namespace)


__all__ = ["parse_pagexml", "PageParseError"]
