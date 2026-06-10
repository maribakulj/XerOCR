"""``TesseractAdapter`` : conformité Module, validations, exécution (mockée)."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from xerocr.adapters.ocr.tesseract import TesseractAdapter, tesseract_binary_version
from xerocr.domain.artifacts import Artifact, ArtifactType
from xerocr.domain.confidence import ConfidenceToken
from xerocr.domain.errors import AdapterStepError, RunCancelledError
from xerocr.pipeline.protocols import Module
from xerocr.pipeline.run_control import RunControl
from xerocr.pipeline.types import RunContext


def _image(path: Path) -> Artifact:
    return Artifact(
        id="doc1:init:image",
        document_id="doc1",
        type=ArtifactType.IMAGE,
        uri=str(path),
    )


def _ctx(workspace: Path | None) -> RunContext:
    return RunContext(
        document_id="doc1",
        code_version="t",
        pipeline_name="p",
        workspace_uri=None if workspace is None else str(workspace),
    )


def _mock_ocr(monkeypatch: pytest.MonkeyPatch, text: str) -> None:
    monkeypatch.setattr(
        "xerocr.adapters.ocr.tesseract._invoke_tesseract", lambda **_: text
    )
    monkeypatch.setattr(
        "xerocr.adapters.ocr.tesseract._invoke_tesseract_confidences",
        lambda **_: [ConfidenceToken(text="mot", confidence=0.93)],
    )


def test_satisfies_module_protocol() -> None:
    adapter = TesseractAdapter(label="fra", lang="fra")
    assert isinstance(adapter, Module)
    assert adapter.name == "tesseract:fra"
    assert adapter.version
    assert adapter.input_types == frozenset({ArtifactType.IMAGE})
    assert adapter.output_types == frozenset(
        {ArtifactType.RAW_TEXT, ArtifactType.CONFIDENCES}
    )


def test_rejects_injection_lang() -> None:
    with pytest.raises(AdapterStepError):
        TesseractAdapter(label="x", lang="fra; rm -rf /")


@pytest.mark.parametrize(
    "kwargs",
    [{"label": "bad label"}, {"label": "x", "psm": 99}, {"label": "x", "oem": 9}],
)
def test_rejects_invalid_config(kwargs: dict) -> None:
    with pytest.raises(AdapterStepError):
        TesseractAdapter(**kwargs)


def test_execute_writes_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _mock_ocr(monkeypatch, "Texte reconnu")
    adapter = TesseractAdapter(label="fra", lang="fra")
    out = adapter.execute(
        {ArtifactType.IMAGE: _image(tmp_path / "doc1.png")},
        {},
        _ctx(tmp_path),
        RunControl(),
    )
    artifact = out.artifacts[ArtifactType.RAW_TEXT]
    assert artifact.type == ArtifactType.RAW_TEXT
    assert artifact.uri is not None
    assert Path(artifact.uri).read_text(encoding="utf-8") == "Texte reconnu"
    assert artifact.content_hash is not None


def test_requires_workspace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _mock_ocr(monkeypatch, "x")
    adapter = TesseractAdapter(label="fra")
    with pytest.raises(AdapterStepError):
        adapter.execute(
            {ArtifactType.IMAGE: _image(tmp_path / "doc1.png")},
            {},
            _ctx(None),
            RunControl(),
        )


def test_requires_image(tmp_path: Path) -> None:
    adapter = TesseractAdapter(label="fra")
    with pytest.raises(AdapterStepError):
        adapter.execute({}, {}, _ctx(tmp_path), RunControl())


def test_cancellation_raises(tmp_path: Path) -> None:
    adapter = TesseractAdapter(label="fra")
    control = RunControl()
    control.trigger_cancel()
    with pytest.raises(RunCancelledError):
        adapter.execute(
            {ArtifactType.IMAGE: _image(tmp_path / "doc1.png")},
            {},
            _ctx(tmp_path),
            control,
        )


@pytest.mark.live
def test_live_real_tesseract(tmp_path: Path) -> None:
    if shutil.which("tesseract") is None:
        pytest.skip("binaire tesseract absent")
    pytest.importorskip("pytesseract")
    pil_image = pytest.importorskip("PIL.Image")
    from PIL import ImageDraw

    canvas = pil_image.new("RGB", (220, 64), "white")
    ImageDraw.Draw(canvas).text((10, 20), "Hello", fill="black")
    image_path = tmp_path / "doc1.png"
    canvas.save(image_path)
    adapter = TesseractAdapter(label="eng", lang="eng")
    out = adapter.execute(
        {ArtifactType.IMAGE: _image(image_path)}, {}, _ctx(tmp_path), RunControl()
    )
    assert out.artifacts[ArtifactType.RAW_TEXT].uri is not None


def test_execute_writes_confidences_sidecar(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _mock_ocr(monkeypatch, "mot")
    adapter = TesseractAdapter(label="fra", lang="fra")
    out = adapter.execute(
        {ArtifactType.IMAGE: _image(tmp_path)}, {}, _ctx(tmp_path), RunControl()
    )
    sidecar = out.artifacts[ArtifactType.CONFIDENCES]
    assert sidecar.uri is not None
    tokens = json.loads(Path(sidecar.uri).read_text(encoding="utf-8"))
    assert tokens == [{"text": "mot", "confidence": 0.93}]


def test_confidences_failure_degrades_to_empty_sidecar(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Best-effort : l'extraction qui casse ne fait pas échouer l'OCR.
    monkeypatch.setattr(
        "xerocr.adapters.ocr.tesseract._invoke_tesseract", lambda **_: "mot"
    )

    def boom(**_: object) -> list[ConfidenceToken]:
        raise RuntimeError("tsv illisible")

    monkeypatch.setattr(
        "xerocr.adapters.ocr.tesseract._invoke_tesseract_confidences", boom
    )
    out = TesseractAdapter(label="fra", lang="fra").execute(
        {ArtifactType.IMAGE: _image(tmp_path)}, {}, _ctx(tmp_path), RunControl()
    )
    sidecar = out.artifacts[ArtifactType.CONFIDENCES]
    assert sidecar.uri is not None
    assert json.loads(Path(sidecar.uri).read_text(encoding="utf-8")) == []


# --- Version du binaire → RunManifest (reproductibilité, §12) ------------------


def _completed(stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=["tesseract", "--version"], returncode=0, stdout=stdout, stderr=stderr
    )


def test_binary_version_reads_first_nonempty_line() -> None:
    # Bannière sur stdout : on garde la 1ʳᵉ ligne non vide (« tesseract 5.3.0 »).
    banner = "tesseract 5.3.0\n leptonica-1.82.0\n"
    assert tesseract_binary_version(run=lambda *a, **k: _completed(stdout=banner)) == (
        "tesseract 5.3.0"
    )


def test_binary_version_reads_from_stderr() -> None:
    # Certains builds émettent la bannière sur stderr : on la lit quand même.
    banner = _completed(stderr="tesseract 5.4.1\n")
    assert tesseract_binary_version(run=lambda *a, **k: banner) == "tesseract 5.4.1"


def test_binary_version_none_when_absent() -> None:
    # Binaire absent ou timeout → None (best-effort, jamais une panne).
    def absent(*_a: object, **_k: object) -> subprocess.CompletedProcess[str]:
        raise FileNotFoundError("tesseract")

    assert tesseract_binary_version(run=absent) is None

    def slow(*_a: object, **_k: object) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(cmd="tesseract", timeout=10)

    assert tesseract_binary_version(run=slow) is None


def test_system_binaries_hook_reports_version(monkeypatch: pytest.MonkeyPatch) -> None:
    # Le hook de provenance expose la version baquée → alimente system_binaries_lock.
    monkeypatch.setattr(
        "xerocr.adapters.ocr.tesseract.tesseract_binary_version",
        lambda: "tesseract 5.3.0",
    )
    assert TesseractAdapter(label="fra").system_binaries() == {
        "tesseract": "tesseract 5.3.0"
    }


def test_system_binaries_hook_empty_when_binary_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "xerocr.adapters.ocr.tesseract.tesseract_binary_version", lambda: None
    )
    assert TesseractAdapter(label="fra").system_binaries() == {}
