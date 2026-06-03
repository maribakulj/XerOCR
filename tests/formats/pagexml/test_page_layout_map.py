"""Mapper ``page_to_layout`` + consommateur réel (chargement d'une GT PAGE).

Pendant PAGE de la tranche ALTO→layout : projection structurelle (polygones,
lignes sans mots, ordre de lecture en arbre, régions non-texte) puis bout-en-bout
``region_cer`` sur une GT **sourcée PAGE** via ``load_representation`` (qui
distingue PAGE d'ALTO au marqueur de racine).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from xerocr.domain.artifacts import ArtifactType
from xerocr.domain.layout import CanonicalLayout, LayoutPage, Line, Region
from xerocr.evaluation.context import DocContext
from xerocr.evaluation.metrics.layout import region_cer
from xerocr.evaluation.representations import load_representation
from xerocr.formats.pagexml import (
    PageDocument,
    PageGenericRegion,
    PagePage,
    PageTextLine,
    PageTextRegion,
    ReadingOrderGroup,
    ReadingOrderRef,
    write_pagexml,
)
from xerocr.formats.pagexml.layout_map import page_to_layout


def _text_region(rid: str, text: str) -> PageTextRegion:
    return PageTextRegion(
        id=rid,
        coords=((0, 0), (100, 0), (100, 30)),
        text_lines=(PageTextLine(id=f"{rid}_l1", text=text),),
    )


def _doc(*regions: PageTextRegion) -> PageDocument:
    return PageDocument(
        pages=(PagePage(image_width=100, image_height=50, regions=regions),)
    )


def test_maps_text_region_line_and_polygon_geometry() -> None:
    line = PageTextLine(
        id="l1",
        coords=((0, 0), (100, 0), (100, 30)),
        baseline=((0, 25), (100, 25)),
        text="Bonjour",
    )
    region = PageTextRegion(id="r1", region_type="paragraph", text_lines=(line,))
    layout = page_to_layout(_doc(region))
    page = layout.pages[0]
    assert (page.width, page.height) == (100, 50)
    r1 = page.regions[0]
    assert r1.id == "r1" and r1.region_type == "paragraph"
    assert r1.lines[0].text == "Bonjour"
    assert r1.lines[0].words == ()  # PAGE n'a pas de niveau mot
    assert r1.lines[0].baseline == ((0, 25), (100, 25))
    assert r1.lines[0].geometry is not None
    assert r1.lines[0].geometry.bbox is None  # PAGE = polygones uniquement
    assert r1.lines[0].geometry.polygon == ((0, 0), (100, 0), (100, 30))


def test_reading_order_tree_flattened() -> None:
    ro = ReadingOrderGroup(
        children=(
            ReadingOrderRef(region_ref="r2"),
            ReadingOrderGroup(children=(ReadingOrderRef(region_ref="r1"),)),
        )
    )
    page = PagePage(
        regions=(_text_region("r1", "a"), _text_region("r2", "b")),
        reading_order=ro,
    )
    assert page_to_layout(PageDocument(pages=(page,))).pages[0].reading_order == (
        "r2",
        "r1",
    )


def test_generic_region_keeps_prima_name_and_has_no_lines() -> None:
    image = PageGenericRegion(region_name="ImageRegion", id="img1")
    doc = PageDocument(pages=(PagePage(regions=(image,)),))
    region = page_to_layout(doc).pages[0].regions[0]
    assert region.region_type == "ImageRegion"
    assert region.lines == ()


def test_nested_regions_preserved() -> None:
    inner = PageGenericRegion(region_name="SeparatorRegion", id="sep1")
    outer = PageTextRegion(
        id="r1", text_lines=(PageTextLine(text="x"),), regions=(inner,)
    )
    region = page_to_layout(_doc(outer)).pages[0].regions[0]
    assert region.regions[0].id == "sep1"
    assert region.regions[0].region_type == "SeparatorRegion"


def test_synthesizes_missing_region_ids() -> None:
    doc = PageDocument(pages=(PagePage(regions=(_text_region("", "a"),)),))
    # id="" est falsy → synthétisé.
    assert page_to_layout(doc).pages[0].regions[0].id == "region_0"


def test_load_representation_reads_page_as_layout(tmp_path: Path) -> None:
    path = tmp_path / "gt.page.xml"
    path.write_bytes(write_pagexml(_doc(_text_region("r1", "hello world"))))
    loaded = load_representation(str(path), ArtifactType.LAYOUT)
    region = loaded.pages[0].regions[0]  # type: ignore[attr-defined]
    assert region.lines[0].text == "hello world"


def _gt_via_page(tmp_path: Path) -> str:
    path = tmp_path / "doc1.gt.page.xml"
    path.write_bytes(
        write_pagexml(
            _doc(_text_region("r1", "hello world"), _text_region("r2", "second block"))
        )
    )
    return str(path)


def test_region_cer_end_to_end_over_page_gt(tmp_path: Path) -> None:
    gt = load_representation(_gt_via_page(tmp_path), ArtifactType.LAYOUT)
    hyp = CanonicalLayout(
        pages=(
            LayoutPage(
                regions=(
                    Region(id="r1", lines=(Line(text="hello world"),)),
                    Region(id="r2", lines=(Line(text="second blocX"),)),
                ),
            ),
        )
    )
    score = region_cer.fn(DocContext(document_id="doc1", reference=gt, hypothesis=hyp))
    assert score is not None
    assert score.value == pytest.approx(1 / 23)  # 1 faute / (11 + 12) chars
