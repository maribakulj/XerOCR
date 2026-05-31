"""``PrecomputedTextAdapter`` — lecture de texte pré-calculé, en tant que Module."""

from __future__ import annotations

from pathlib import Path

import pytest

from xerocr.adapters.ocr.precomputed import PrecomputedTextAdapter
from xerocr.domain.artifacts import Artifact, ArtifactType
from xerocr.domain.errors import AdapterStepError, RunCancelledError
from xerocr.pipeline.protocols import Module
from xerocr.pipeline.run_control import RunControl
from xerocr.pipeline.types import RunContext


def _ctx() -> RunContext:
    return RunContext(document_id="doc1", code_version="t", pipeline_name="p")


def _image(path: Path) -> Artifact:
    return Artifact(
        id="doc1:init:image",
        document_id="doc1",
        type=ArtifactType.IMAGE,
        uri=str(path),
    )


def test_satisfies_module_protocol() -> None:
    adapter = PrecomputedTextAdapter(source_label="tesseract")
    assert isinstance(adapter, Module)
    assert adapter.name == "precomputed:tesseract"
    assert adapter.version
    assert adapter.input_types == frozenset({ArtifactType.IMAGE})
    assert adapter.output_types == frozenset({ArtifactType.RAW_TEXT})


def test_reads_precomputed_text(tmp_path: Path) -> None:
    image = tmp_path / "folio_001.png"
    (tmp_path / "folio_001.tesseract.txt").write_text(
        "Icy commence le prologue", encoding="utf-8"
    )
    adapter = PrecomputedTextAdapter(source_label="tesseract")
    out = adapter.execute(
        {ArtifactType.IMAGE: _image(image)}, {}, _ctx(), RunControl()
    )
    art = out[ArtifactType.RAW_TEXT]
    assert art.type == ArtifactType.RAW_TEXT
    assert art.uri is not None and art.uri.endswith("folio_001.tesseract.txt")
    assert art.content_hash is not None
    assert len(art.content_hash) == 64


def test_missing_file_raises(tmp_path: Path) -> None:
    adapter = PrecomputedTextAdapter(source_label="tesseract")
    with pytest.raises(AdapterStepError):
        adapter.execute(
            {ArtifactType.IMAGE: _image(tmp_path / "absent.png")},
            {}, _ctx(), RunControl(),
        )


def test_missing_image_raises() -> None:
    adapter = PrecomputedTextAdapter(source_label="tesseract")
    with pytest.raises(AdapterStepError):
        adapter.execute({}, {}, _ctx(), RunControl())


def test_non_utf8_raises(tmp_path: Path) -> None:
    image = tmp_path / "doc.png"
    (tmp_path / "doc.bad.txt").write_bytes(b"\xff\xfe\x00\x01")
    adapter = PrecomputedTextAdapter(source_label="bad")
    with pytest.raises(AdapterStepError):
        adapter.execute(
            {ArtifactType.IMAGE: _image(image)}, {}, _ctx(), RunControl()
        )


def test_invalid_label_raises() -> None:
    with pytest.raises(AdapterStepError):
        PrecomputedTextAdapter(source_label="bad label!")


def test_cancellation_raises(tmp_path: Path) -> None:
    image = tmp_path / "doc.png"
    (tmp_path / "doc.tesseract.txt").write_text("x", encoding="utf-8")
    adapter = PrecomputedTextAdapter(source_label="tesseract")
    control = RunControl()
    control.trigger_cancel()
    with pytest.raises(RunCancelledError):
        adapter.execute(
            {ArtifactType.IMAGE: _image(image)}, {}, _ctx(), control
        )
