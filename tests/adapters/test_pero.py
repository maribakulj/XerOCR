"""``PeroAdapter`` : contrat module, validations, exécution (invoke mocké)."""

from __future__ import annotations

from pathlib import Path

import pytest

from xerocr.adapters.ocr.pero import PeroAdapter
from xerocr.domain.artifacts import Artifact, ArtifactType
from xerocr.domain.errors import AdapterStepError
from xerocr.pipeline.protocols import Module
from xerocr.pipeline.run_control import RunControl
from xerocr.pipeline.types import RunContext


def _ctx(workspace: Path) -> RunContext:
    return RunContext(
        document_id="d1", code_version="t", pipeline_name="p",
        workspace_uri=str(workspace),
    )


def _image(tmp_path: Path) -> Artifact:
    path = tmp_path / "page.png"
    path.write_bytes(b"\x89PNG\r\n\x1a\n")
    return Artifact(
        id="d1:img", document_id="d1", type=ArtifactType.IMAGE, uri=str(path)
    )


def test_satisfies_module_protocol() -> None:
    adapter = PeroAdapter(label="anc", model="config.ini")
    assert isinstance(adapter, Module)
    assert adapter.name == "pero:anc"
    assert adapter.input_types == frozenset({ArtifactType.IMAGE})
    assert adapter.output_types == frozenset({ArtifactType.RAW_TEXT})


def test_model_is_required() -> None:
    with pytest.raises(AdapterStepError):
        PeroAdapter(label="anc", model="")


def test_rejects_bad_label() -> None:
    with pytest.raises(AdapterStepError):
        PeroAdapter(label="mauvais label", model="config.ini")


def test_execute_writes_text(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "xerocr.adapters.ocr.pero._invoke_pero",
        lambda **_: "ligne une\nligne deux",
    )
    out = PeroAdapter(label="anc", model="config.ini").execute(
        {ArtifactType.IMAGE: _image(tmp_path)}, {}, _ctx(tmp_path), RunControl()
    )
    artifact = out.artifacts[ArtifactType.RAW_TEXT]
    assert artifact.uri is not None
    assert Path(artifact.uri).read_text(encoding="utf-8") == "ligne une\nligne deux"


def test_missing_image_raises(tmp_path: Path) -> None:
    with pytest.raises(AdapterStepError):
        PeroAdapter(label="anc", model="config.ini").execute(
            {}, {}, _ctx(tmp_path), RunControl()
        )
