"""``crop_region`` + fan-out **avec découpage réel** (pipeline hybride seg→OCR).

Déterministe sans Tesseract : image synthétique + recognizer factice qui renvoie
la **taille du crop reçu** — prouve que le fan-out passe à l'OCR la vraie
sous-image du bloc (pas l'image entière), unités neutralisées.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from xerocr.adapters.layout.crop import crop_region
from xerocr.domain.artifacts import Artifact, ArtifactType
from xerocr.domain.errors import AdapterStepError
from xerocr.domain.layout import BBox, CanonicalLayout, Geometry, LayoutPage, Region
from xerocr.pipeline.fanout import run_region_fanout
from xerocr.pipeline.run_control import RunControl
from xerocr.pipeline.types import RunContext

Image = pytest.importorskip("PIL.Image")


def _ctx(tmp_path: Path) -> RunContext:
    return RunContext(
        document_id="doc1",
        code_version="1.0",
        pipeline_name="seg",
        workspace_uri=str(tmp_path),
    )


def _page_image(tmp_path: Path, size: tuple[int, int]) -> Artifact:
    path = tmp_path / "page.png"
    Image.new("RGB", size, "white").save(path)
    return Artifact(
        id="doc1:init:image", document_id="doc1", type=ArtifactType.IMAGE, uri=str(path)
    )


class _SizeRecognizer:
    """Recognizer factice : RAW_TEXT = dimensions du crop reçu (``WxH``)."""

    name = "fake:size"
    version = "0.1"
    input_types = frozenset({ArtifactType.IMAGE})
    output_types = frozenset({ArtifactType.RAW_TEXT})

    def execute(self, inputs, params, context, control):  # noqa: ANN001, ANN201
        image = inputs[ArtifactType.IMAGE]
        with Image.open(image.uri) as im:
            w, h = im.size
        out = Path(context.workspace_uri) / f"{image.region_id}.txt"
        out.write_text(f"{w}x{h}", encoding="utf-8")
        return {
            ArtifactType.RAW_TEXT: Artifact(
                id=f"{context.document_id}:{image.region_id}:raw",
                document_id=context.document_id,
                type=ArtifactType.RAW_TEXT,
                uri=str(out),
                region_id=image.region_id,
            )
        }


def test_crop_region_extracts_relative_box(tmp_path: Path) -> None:
    page = _page_image(tmp_path, (100, 50))
    crop = crop_region(page, (0.0, 0.0, 0.5, 1.0), "r1", _ctx(tmp_path))
    assert crop.type is ArtifactType.IMAGE and crop.region_id == "r1"
    with Image.open(crop.uri) as im:
        assert im.size == (50, 50)  # 0.5×100 × 1.0×50


def test_crop_region_rejects_empty_box(tmp_path: Path) -> None:
    page = _page_image(tmp_path, (100, 50))
    with pytest.raises(AdapterStepError, match="boîte vide"):
        crop_region(page, (0.5, 0.0, 0.5, 1.0), "r1", _ctx(tmp_path))


def test_fanout_with_cropper_feeds_real_block_image(tmp_path: Path) -> None:
    page = _page_image(tmp_path, (100, 50))
    layout = CanonicalLayout(
        pages=(
            LayoutPage(
                width=100,
                height=50,
                regions=(
                    Region(
                        id="r1",
                        geometry=Geometry(bbox=BBox(x=0, y=0, width=50, height=50)),
                    ),
                    Region(
                        id="r2",
                        geometry=Geometry(bbox=BBox(x=50, y=0, width=50, height=50)),
                    ),
                ),
            ),
        )
    )
    filled = run_region_fanout(
        layout=layout,
        page_image=page,
        recognizer=_SizeRecognizer(),
        context=_ctx(tmp_path),
        control=RunControl(),
        cropper=crop_region,
    )
    texts = [r.lines[0].text for r in filled.pages[0].regions]
    assert texts == ["50x50", "50x50"]  # chaque bloc a reçu sa sous-image, pas la page


def test_fanout_skips_region_without_geometry(tmp_path: Path) -> None:
    page = _page_image(tmp_path, (100, 50))
    layout = CanonicalLayout(
        pages=(LayoutPage(width=100, height=50, regions=(Region(id="r1"),)),)
    )
    filled = run_region_fanout(
        layout=layout,
        page_image=page,
        recognizer=_SizeRecognizer(),
        context=_ctx(tmp_path),
        control=RunControl(),
        cropper=crop_region,
    )
    assert filled.pages[0].regions[0].lines == ()  # pas de géométrie → non découpable
