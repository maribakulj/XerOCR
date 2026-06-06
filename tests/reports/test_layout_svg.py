"""Rendu SVG d'un ``CanonicalLayout`` : régions → boîtes, déterminisme, échappement."""

from __future__ import annotations

from xerocr.domain.layout import BBox, CanonicalLayout, Geometry, LayoutPage, Region
from xerocr.reports.layout_svg import layout_to_svg


def _layout(*regions: Region, width: int = 200, height: int = 100) -> CanonicalLayout:
    return CanonicalLayout(
        pages=(LayoutPage(width=width, height=height, regions=regions),)
    )


def _region(rid: str, *, rtype: str | None = None, box: BBox | None = None) -> Region:
    geom = Geometry(bbox=box) if box else None
    return Region(id=rid, region_type=rtype, geometry=geom)


def test_empty_layout_is_minimal_valid_svg() -> None:
    svg = layout_to_svg(CanonicalLayout())
    assert svg.startswith("<svg")
    assert "viewBox" in svg


def test_renders_one_rect_and_label_per_region() -> None:
    layout = _layout(
        _region("r1", rtype="title", box=BBox(x=10, y=5, width=80, height=20)),
        _region("r2", rtype="text", box=BBox(x=10, y=40, width=80, height=50)),
    )
    svg = layout_to_svg(layout)
    assert svg.count("<rect") == 3  # fond de page + 2 régions
    assert svg.count("<text") == 2
    assert ">title<" in svg
    assert ">text<" in svg
    assert 'viewBox="0 0 200 100"' in svg


def test_label_falls_back_to_id_when_no_type() -> None:
    region = _region("only-id", box=BBox(x=0, y=0, width=5, height=5))
    svg = layout_to_svg(_layout(region))
    assert ">only-id<" in svg


def test_image_href_places_background_image() -> None:
    layout = _layout(_region("r1", box=BBox(x=0, y=0, width=10, height=10)))
    svg = layout_to_svg(layout, image_href="/api/segmentation/abc/image")
    assert '<image href="/api/segmentation/abc/image"' in svg
    # avec image de fond, pas de rectangle de fond neutre (que les régions)
    assert svg.count("<rect") == 1


def test_label_is_html_escaped() -> None:
    layout = _layout(_region("r1", rtype="<x>&", box=BBox(x=0, y=0, width=5, height=5)))
    svg = layout_to_svg(layout)
    assert "<x>&" not in svg
    assert "&lt;x&gt;&amp;" in svg


def test_render_is_deterministic() -> None:
    layout = _layout(
        _region("r1", rtype="a", box=BBox(x=1, y=2, width=3, height=4)),
        _region("r2", rtype="b", box=BBox(x=5, y=6, width=7, height=8)),
    )
    assert layout_to_svg(layout) == layout_to_svg(layout)


def test_region_without_geometry_is_skipped() -> None:
    layout = _layout(
        _region("r1", rtype="a", box=BBox(x=0, y=0, width=5, height=5)),
        _region("no-geom"),  # aucune boîte → ni rect ni label
    )
    svg = layout_to_svg(layout)
    assert svg.count("<text") == 1
    assert ">no-geom<" not in svg


def test_page_size_from_region_envelope_when_dims_absent() -> None:
    layout = CanonicalLayout(
        pages=(
            LayoutPage(
                regions=(_region("r1", box=BBox(x=10, y=10, width=40, height=30)),)
            ),
        )
    )
    svg = layout_to_svg(layout)
    assert 'viewBox="0 0 50 40"' in svg
