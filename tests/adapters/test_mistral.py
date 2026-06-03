"""``MistralAdapter`` : conformité Module, post-correction (mockée)."""

from __future__ import annotations

from pathlib import Path

import pytest

from xerocr.adapters.llm.mistral import MistralAdapter
from xerocr.domain.artifacts import Artifact, ArtifactType
from xerocr.domain.errors import AdapterStepError, RunCancelledError
from xerocr.pipeline.protocols import Module
from xerocr.pipeline.run_control import RunControl
from xerocr.pipeline.types import RunContext


def _raw_text(path: Path) -> Artifact:
    return Artifact(
        id="doc1:ocr:raw_text",
        document_id="doc1",
        type=ArtifactType.RAW_TEXT,
        uri=str(path),
    )


def _ctx(workspace: Path) -> RunContext:
    return RunContext(
        document_id="doc1",
        code_version="t",
        pipeline_name="p",
        workspace_uri=str(workspace),
    )


def _mock(monkeypatch: pytest.MonkeyPatch, text: str) -> None:
    monkeypatch.setattr(
        "xerocr.adapters.llm.mistral._invoke_mistral", lambda **_: text
    )


def test_satisfies_module_protocol() -> None:
    adapter = MistralAdapter(label="ministral", model="mistral-small-latest")
    assert isinstance(adapter, Module)
    assert adapter.name == "mistral:ministral"
    assert adapter.input_types == frozenset({ArtifactType.RAW_TEXT})
    assert adapter.output_types == frozenset({ArtifactType.CORRECTED_TEXT})


def test_invalid_label_rejected() -> None:
    with pytest.raises(AdapterStepError):
        MistralAdapter(label="bad label")


def test_execute_produces_corrected_text(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "ocr.txt").write_text("Hello wrld", encoding="utf-8")
    _mock(monkeypatch, "Hello world")
    adapter = MistralAdapter(label="m")
    out = adapter.execute(
        {ArtifactType.RAW_TEXT: _raw_text(tmp_path / "ocr.txt")},
        {},
        _ctx(tmp_path),
        RunControl(),
    )
    artifact = out[ArtifactType.CORRECTED_TEXT]
    assert artifact.type == ArtifactType.CORRECTED_TEXT
    assert artifact.uri is not None
    assert Path(artifact.uri).read_text(encoding="utf-8") == "Hello world"
    assert artifact.content_hash is not None


def test_requires_workspace() -> None:
    adapter = MistralAdapter(label="m")
    ctx = RunContext(document_id="doc1", code_version="t", pipeline_name="p")
    with pytest.raises(AdapterStepError):
        adapter.execute(
            {ArtifactType.RAW_TEXT: _raw_text(Path("/tmp/x"))}, {}, ctx, RunControl()
        )


def test_missing_input_raises(tmp_path: Path) -> None:
    adapter = MistralAdapter(label="m")
    with pytest.raises(AdapterStepError):
        adapter.execute({}, {}, _ctx(tmp_path), RunControl())


def test_cancellation_raises(tmp_path: Path) -> None:
    adapter = MistralAdapter(label="m")
    control = RunControl()
    control.trigger_cancel()
    with pytest.raises(RunCancelledError):
        adapter.execute(
            {ArtifactType.RAW_TEXT: _raw_text(tmp_path / "x.txt")},
            {},
            _ctx(tmp_path),
            control,
        )
