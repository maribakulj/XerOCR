"""Tests du format ALTO : parsing, round-trip C14N, déterminisme, sécurité."""

from __future__ import annotations

import pytest

from xerocr.formats.alto import (
    AltoBBox,
    AltoComposedBlock,
    AltoDocument,
    AltoGraphicalElement,
    AltoIllustration,
    AltoLine,
    AltoPage,
    AltoParseError,
    AltoString,
    AltoTextBlock,
    parse_alto,
    write_alto,
)
from xerocr.formats.alto.writer import AltoWriteError

_ALTO_V4 = b"""<?xml version="1.0" encoding="UTF-8"?>
<alto xmlns="http://www.loc.gov/standards/alto/ns-v4#">
  <Description><MeasurementUnit>pixel</MeasurementUnit></Description>
  <Layout>
    <Page ID="p1" WIDTH="1000" HEIGHT="1400">
      <PrintSpace>
        <TextBlock ID="b1" TYPE="paragraph"
                   HPOS="10" VPOS="20" WIDTH="500" HEIGHT="100">
          <TextLine ID="l1" BASELINE="10,50 510,50"
                    HPOS="10" VPOS="20" WIDTH="500" HEIGHT="40">
            <String ID="w1" CONTENT="Bonjour" WC="0.98"
                    HPOS="10" VPOS="20" WIDTH="200" HEIGHT="40"/>
            <String ID="w2" CONTENT="monde"
                    HPOS="220" VPOS="20" WIDTH="150" HEIGHT="40"/>
          </TextLine>
        </TextBlock>
        <Illustration ID="img1"
                      HPOS="10" VPOS="200" WIDTH="300" HEIGHT="300"/>
      </PrintSpace>
    </Page>
  </Layout>
</alto>"""


def _rich_doc() -> AltoDocument:
    s1 = AltoString(
        content="Bonjour",
        id="w1",
        bbox=AltoBBox(hpos=10, vpos=20, width=200, height=40),
        confidence=0.98,
        subs_type="HypPart1",
        subs_content="Bonjour-monde",
    )
    s2 = AltoString(
        content="monde", id="w2", bbox=AltoBBox(hpos=220, vpos=20, width=150, height=40)
    )
    line = AltoLine(
        id="l1",
        bbox=AltoBBox(hpos=10, vpos=20, width=500, height=40),
        polygon=((10, 20), (510, 20), (510, 60)),
        baseline=((10, 50), (510, 50)),
        strings=(s1, s2),
    )
    text_block = AltoTextBlock(
        id="b1",
        block_type="paragraph",
        bbox=AltoBBox(hpos=10, vpos=20, width=500, height=100),
        lines=(line,),
    )
    illustration = AltoIllustration(
        id="img1", bbox=AltoBBox(hpos=10, vpos=200, width=300, height=300)
    )
    graphic = AltoGraphicalElement(id="g1", polygon=((0, 0), (5, 0), (5, 5)))
    composed = AltoComposedBlock(
        id="c1", block_type="article", blocks=(text_block, illustration)
    )
    page = AltoPage(id="p1", width=1000, height=1400, blocks=(composed, graphic))
    return AltoDocument(pages=(page,), source_version="v4", measurement_unit="pixel")


# --- parsing -----------------------------------------------------------------


def test_parse_version_and_unit() -> None:
    doc = parse_alto(_ALTO_V4)
    assert doc.source_version == "v4"
    assert doc.measurement_unit == "pixel"


@pytest.mark.parametrize(
    ("ns", "expected"),
    [
        ("http://www.loc.gov/standards/alto/ns-v2#", "v2"),
        ("http://www.loc.gov/standards/alto/ns-v3#", "v3"),
        ("http://www.loc.gov/standards/alto/ns-v4#", "v4"),
    ],
)
def test_parse_version_detection(ns: str, expected: str) -> None:
    data = f'<alto xmlns="{ns}"><Layout><Page/></Layout></alto>'.encode()
    assert parse_alto(data).source_version == expected


def test_parse_no_namespace() -> None:
    data = b"<alto><Layout><Page/></Layout></alto>"
    assert parse_alto(data).source_version == "none"


def test_parse_structure_and_geometry() -> None:
    doc = parse_alto(_ALTO_V4)
    page = doc.pages[0]
    assert page.id == "p1" and page.width == 1000 and page.height == 1400
    block = page.blocks[0]
    assert isinstance(block, AltoTextBlock)
    assert block.block_type == "paragraph"
    assert block.bbox == AltoBBox(hpos=10, vpos=20, width=500, height=100)
    line = block.lines[0]
    assert line.baseline == ((10, 50), (510, 50))
    assert line.strings[0].content == "Bonjour"
    assert line.strings[0].confidence == 0.98
    assert line.strings[1].confidence is None


def test_parse_non_text_region() -> None:
    doc = parse_alto(_ALTO_V4)
    illustration = doc.pages[0].blocks[1]
    assert isinstance(illustration, AltoIllustration)
    assert illustration.id == "img1"


def test_parse_composed_block_recursion() -> None:
    data = b"""<alto xmlns="http://www.loc.gov/standards/alto/ns-v4#"><Layout>
      <Page><PrintSpace>
        <ComposedBlock ID="c1" TYPE="article">
          <TextBlock ID="b1"><TextLine><String CONTENT="hi"/></TextLine></TextBlock>
        </ComposedBlock>
      </PrintSpace></Page></Layout></alto>"""
    composed = parse_alto(data).pages[0].blocks[0]
    assert isinstance(composed, AltoComposedBlock)
    assert composed.block_type == "article"
    assert isinstance(composed.blocks[0], AltoTextBlock)


def test_parse_polygon() -> None:
    data = b"""<alto xmlns="http://www.loc.gov/standards/alto/ns-v4#"><Layout>
      <Page><PrintSpace><TextBlock><TextLine>
        <Shape><Polygon POINTS="0,0 10,0 10,10"/></Shape>
        <String CONTENT="x"/>
      </TextLine></TextBlock></PrintSpace></Page></Layout></alto>"""
    line = parse_alto(data).pages[0].blocks[0]
    assert isinstance(line, AltoTextBlock)
    assert line.lines[0].polygon == ((0, 0), (10, 0), (10, 10))


def test_parse_tolerates_negative_coords() -> None:
    data = b"""<alto xmlns="http://www.loc.gov/standards/alto/ns-v4#"><Layout>
      <Page><PrintSpace><TextBlock HPOS="-5" VPOS="0" WIDTH="10" HEIGHT="10">
      </TextBlock></PrintSpace></Page></Layout></alto>"""
    block = parse_alto(data).pages[0].blocks[0]
    assert isinstance(block, AltoTextBlock)
    assert block.bbox is not None and block.bbox.hpos == -5


# --- round-trip & déterminisme ----------------------------------------------


def test_roundtrip_preserves_model() -> None:
    doc = _rich_doc()
    assert parse_alto(write_alto(doc)) == doc


def test_writer_is_deterministic() -> None:
    doc = _rich_doc()
    assert write_alto(doc) == write_alto(doc)


def test_roundtrip_empty_document() -> None:
    doc = AltoDocument(pages=(AltoPage(id="p"),), source_version="v4")
    assert parse_alto(write_alto(doc)) == doc


def test_write_invalid_version_rejected() -> None:
    with pytest.raises(AltoWriteError):
        write_alto(_rich_doc(), version="v9")


# --- erreurs & sécurité ------------------------------------------------------


def test_malformed_raises() -> None:
    with pytest.raises(AltoParseError):
        parse_alto(b"<alto><unclosed>")


def test_empty_raises() -> None:
    with pytest.raises(AltoParseError):
        parse_alto(b"")


def test_doctype_rejected() -> None:
    data = (
        b'<?xml version="1.0"?>'
        b'<!DOCTYPE alto [<!ENTITY x SYSTEM "file:///etc/passwd">]>'
        b'<alto xmlns="http://www.loc.gov/standards/alto/ns-v4#"><Layout/></alto>'
    )
    with pytest.raises(AltoParseError):
        parse_alto(data)
