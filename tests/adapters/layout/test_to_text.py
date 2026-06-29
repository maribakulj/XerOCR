"""``LayoutToTextExtractor`` : aplatissement ``LAYOUT → RAW_TEXT``, ordre de lecture."""

from __future__ import annotations

from pathlib import Path

import pytest

from cinoc.adapters.layout.to_text import LayoutToTextExtractor
from cinoc.domain.artifacts import Artifact, ArtifactType
from cinoc.domain.errors import AdapterStepError
from cinoc.domain.layout import CanonicalLayout, LayoutPage, Line, Region
from cinoc.pipeline.protocols import Module
from cinoc.pipeline.run_control import RunControl
from cinoc.pipeline.types import RunContext


def _ctx(workspace: Path) -> RunContext:
    return RunContext(
        document_id="d1", code_version="t", pipeline_name="p",
        workspace_uri=str(workspace),
    )


def _layout_artifact(tmp_path: Path, layout: CanonicalLayout) -> Artifact:
    path = tmp_path / "d1.layout.json"
    path.write_bytes(layout.model_dump_json().encode("utf-8"))
    return Artifact(
        id="d1:layout", document_id="d1", type=ArtifactType.LAYOUT, uri=str(path)
    )


def test_extractor_honours_module_protocol() -> None:
    ext = LayoutToTextExtractor(label="c0")
    assert isinstance(ext, Module)
    assert ext.name == "layout_to_text:c0"
    assert ext.input_types == frozenset({ArtifactType.LAYOUT})
    assert ext.output_types == frozenset({ArtifactType.RAW_TEXT})


def test_flattens_regions_in_reading_order(tmp_path: Path) -> None:
    # Régions déclarées dans le désordre ; reading_order impose r1 puis r2.
    layout = CanonicalLayout(
        pages=(
            LayoutPage(
                regions=(
                    Region(id="r2", lines=(Line(text="second"),)),
                    Region(id="r1", lines=(Line(text="hello"), Line(text="world"))),
                ),
                reading_order=("r1", "r2"),
            ),
        )
    )
    out = LayoutToTextExtractor(label="c0").execute(
        {ArtifactType.LAYOUT: _layout_artifact(tmp_path, layout)},
        {}, _ctx(tmp_path), RunControl(),
    )
    raw = out.artifacts[ArtifactType.RAW_TEXT]
    assert raw.uri is not None
    assert Path(raw.uri).read_text(encoding="utf-8") == "hello\nworld\nsecond"


def test_unknown_reading_order_falls_back_to_declared(tmp_path: Path) -> None:
    layout = CanonicalLayout(
        pages=(
            LayoutPage(
                regions=(
                    Region(id="a", lines=(Line(text="alpha"),)),
                    Region(id="b", lines=(Line(text="beta"),)),
                ),
                reading_order=(),  # vide → ordre déclaré
            ),
        )
    )
    out = LayoutToTextExtractor(label="c0").execute(
        {ArtifactType.LAYOUT: _layout_artifact(tmp_path, layout)},
        {}, _ctx(tmp_path), RunControl(),
    )
    assert Path(out.artifacts[ArtifactType.RAW_TEXT].uri).read_text(
        encoding="utf-8"
    ) == "alpha\nbeta"


def test_missing_layout_is_clean_error(tmp_path: Path) -> None:
    with pytest.raises(AdapterStepError, match="LAYOUT manquant"):
        LayoutToTextExtractor(label="c0").execute(
            {}, {}, _ctx(tmp_path), RunControl()
        )
