"""``OllamaAdapter`` : conformité Module, post-correction (mockée), annulation.

La 2ᵉ famille LLM passe **le même contrat** qu'openai, sans cas particulier.
L'appel réseau (``_invoke_ollama``) est ``no cover`` (serveur requis) ; la
**sémantique d'annulation** (annulation vs vraie panne) est prouvée via le
seam testable ``_fail_or_cancel``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from xerocr.adapters.llm._base import LLMCompletion
from xerocr.adapters.llm.ollama import OllamaAdapter, _fail_or_cancel
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
        "xerocr.adapters.llm.ollama._invoke_ollama", lambda **_: LLMCompletion(text)
    )


def test_satisfies_module_protocol() -> None:
    adapter = OllamaAdapter(label="llama", model="llama3")
    assert isinstance(adapter, Module)
    assert adapter.name == "ollama:llama"
    assert adapter.input_types == frozenset({ArtifactType.RAW_TEXT})
    assert adapter.output_types == frozenset({ArtifactType.CORRECTED_TEXT})


def test_invalid_label_rejected() -> None:
    with pytest.raises(AdapterStepError):
        OllamaAdapter(label="bad label")


def test_execute_produces_corrected_text(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "ocr.txt").write_text("Helo wrld", encoding="utf-8")
    _mock(monkeypatch, "Hello world")
    adapter = OllamaAdapter(label="llama")
    out = adapter.execute(
        {ArtifactType.RAW_TEXT: _raw_text(tmp_path / "ocr.txt")},
        {},
        _ctx(tmp_path),
        RunControl(),
    )
    artifact = out.artifacts[ArtifactType.CORRECTED_TEXT]
    assert artifact.type == ArtifactType.CORRECTED_TEXT
    assert artifact.uri is not None
    assert Path(artifact.uri).read_text(encoding="utf-8") == "Hello world"
    assert artifact.content_hash is not None


def test_requires_workspace() -> None:
    adapter = OllamaAdapter(label="llama")
    ctx = RunContext(document_id="doc1", code_version="t", pipeline_name="p")
    with pytest.raises(AdapterStepError):
        adapter.execute(
            {ArtifactType.RAW_TEXT: _raw_text(Path("/tmp/x"))}, {}, ctx, RunControl()
        )


def test_missing_input_raises(tmp_path: Path) -> None:
    adapter = OllamaAdapter(label="llama")
    with pytest.raises(AdapterStepError):
        adapter.execute({}, {}, _ctx(tmp_path), RunControl())


def test_cancellation_raises(tmp_path: Path) -> None:
    adapter = OllamaAdapter(label="llama")
    control = RunControl()
    control.trigger_cancel()
    with pytest.raises(RunCancelledError):
        adapter.execute(
            {ArtifactType.RAW_TEXT: _raw_text(tmp_path / "x.txt")},
            {},
            _ctx(tmp_path),
            control,
        )


def test_fail_or_cancel_when_cancelled_raises_cancel() -> None:
    """Annulation déclenchée → la panne réseau est lue comme une annulation."""
    control = RunControl()
    control.trigger_cancel()
    with pytest.raises(RunCancelledError):
        _fail_or_cancel(control, "llama3", RuntimeError("connection closed"))


def test_fail_or_cancel_when_live_raises_adapter_error() -> None:
    """Sans annulation → vraie panne réseau → AdapterStepError (pas un faux cancel)."""
    with pytest.raises(AdapterStepError):
        _fail_or_cancel(RunControl(), "llama3", RuntimeError("connection refused"))
