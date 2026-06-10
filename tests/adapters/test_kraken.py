"""``KrakenAdapter`` : contrat module, sorties, jetons dérivés à la main."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from xerocr.adapters.ocr.kraken import KrakenAdapter, tokens_from_lines
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
    adapter = KrakenAdapter(label="med", model="med.mlmodel")
    assert isinstance(adapter, Module)
    assert adapter.name == "kraken:med"
    assert adapter.input_types == frozenset({ArtifactType.IMAGE})
    assert adapter.output_types == frozenset(
        {ArtifactType.RAW_TEXT, ArtifactType.CONFIDENCES}
    )


def test_model_parameter_is_required() -> None:
    with pytest.raises(AdapterStepError):
        KrakenAdapter(label="med", model="")


def test_tokens_from_lines_hand_computed() -> None:
    # « ab cd » : « ab » couvre les confiances [0.8, 0.6] → 0.7 ;
    # « cd » couvre [1.0, 0.4] → 0.7 ; l'espace (0.0) n'entre dans aucun mot.
    tokens = tokens_from_lines([("ab cd", [0.8, 0.6, 0.0, 1.0, 0.4])])
    assert [(t.text, t.confidence) for t in tokens] == [
        ("ab", pytest.approx(0.7)),
        ("cd", pytest.approx(0.7)),
    ]


def test_execute_writes_text_and_sidecar(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "xerocr.adapters.ocr.kraken._invoke_kraken",
        lambda **_: [("ligne une", [0.9] * 9), ("ligne deux", [0.5] * 10)],
    )
    out = KrakenAdapter(label="med", model="med.mlmodel").execute(
        {ArtifactType.IMAGE: _image(tmp_path)}, {}, _ctx(tmp_path), RunControl()
    )
    text = Path(out.artifacts[ArtifactType.RAW_TEXT].uri).read_text(  # type: ignore[arg-type]
        encoding="utf-8"
    )
    assert text == "ligne une\nligne deux"
    sidecar = json.loads(
        Path(out.artifacts[ArtifactType.CONFIDENCES].uri).read_text(  # type: ignore[arg-type]
            encoding="utf-8"
        )
    )
    assert {t["text"] for t in sidecar} == {"ligne", "une", "deux"}


def test_missing_image_raises() -> None:
    with pytest.raises(AdapterStepError):
        KrakenAdapter(label="med", model="m.mlmodel").execute(
            {}, {}, _ctx(Path("/tmp")), RunControl()
        )
