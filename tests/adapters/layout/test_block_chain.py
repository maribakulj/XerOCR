"""``BlockChainRecognizer`` : OCR par bloc → correction LLM, re-typé ``RAW_TEXT``.

Composition testée avec deux **faux** sous-modules (OCR + correcteur) : le fan-out
n'a besoin que du contrat ``IMAGE → RAW_TEXT``, et le texte qui ressort doit être
le texte **corrigé** (pas le brut).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cinoc.adapters.layout.block_chain import BlockChainRecognizer
from cinoc.domain.artifacts import Artifact, ArtifactType, compute_content_hash
from cinoc.domain.errors import AdapterStepError
from cinoc.domain.usage import ResourceUsage
from cinoc.pipeline.protocols import Module, ParamValue
from cinoc.pipeline.run_control import RunControl
from cinoc.pipeline.types import RunContext, StepOutput


def _ctx(workspace: Path) -> RunContext:
    return RunContext(
        document_id="d1", code_version="t", pipeline_name="p",
        workspace_uri=str(workspace),
    )


def _text_artifact(
    workspace: Path, name: str, text: str, artifact_type: ArtifactType
) -> Artifact:
    path = workspace / f"{name}.txt"
    payload = text.encode("utf-8")
    path.write_bytes(payload)
    return Artifact(
        id=f"d1:{name}:{artifact_type.value}",
        document_id="d1",
        type=artifact_type,
        uri=str(path),
        content_hash=compute_content_hash(payload),
    )


class _FakeOCR:
    """OCR par bloc : ``IMAGE → RAW_TEXT`` (texte fixe, jetons simulés)."""

    def __init__(self, label: str, text: str) -> None:
        self._label, self._text = label, text

    name = property(lambda self: f"tesseract:{self._label}")
    version = property(lambda self: "9.9")
    input_types = property(lambda self: frozenset({ArtifactType.IMAGE}))
    output_types = property(lambda self: frozenset({ArtifactType.RAW_TEXT}))

    def execute(
        self,
        inputs: dict[ArtifactType, Artifact],
        params: dict[str, ParamValue],
        context: RunContext,
        control: RunControl,
    ) -> StepOutput:
        assert ArtifactType.IMAGE in inputs  # reçoit bien le bloc découpé
        assert context.workspace_uri is not None
        raw = _text_artifact(
            Path(context.workspace_uri), "ocr", self._text, ArtifactType.RAW_TEXT
        )
        return StepOutput(
            artifacts={ArtifactType.RAW_TEXT: raw}, usage=ResourceUsage(tokens_in=3)
        )


class _FakeCorrector:
    """Correcteur LLM : ``RAW_TEXT → CORRECTED_TEXT`` (met en majuscules)."""

    def __init__(self, label: str) -> None:
        self._label = label

    name = property(lambda self: f"openai:{self._label}")
    version = property(lambda self: "1.1")
    input_types = property(lambda self: frozenset({ArtifactType.RAW_TEXT}))
    output_types = property(lambda self: frozenset({ArtifactType.CORRECTED_TEXT}))

    def execute(
        self,
        inputs: dict[ArtifactType, Artifact],
        params: dict[str, ParamValue],
        context: RunContext,
        control: RunControl,
    ) -> StepOutput:
        raw = inputs[ArtifactType.RAW_TEXT]
        assert raw.uri is not None
        text = Path(raw.uri).read_text(encoding="utf-8").upper()
        assert context.workspace_uri is not None
        corrected = _text_artifact(
            Path(context.workspace_uri), "corr", text, ArtifactType.CORRECTED_TEXT
        )
        return StepOutput(
            artifacts={ArtifactType.CORRECTED_TEXT: corrected},
            usage=ResourceUsage(tokens_out=5),
        )


def _image(workspace: Path) -> dict[ArtifactType, Artifact]:
    path = workspace / "block.png"
    path.write_bytes(b"\x89PNG block")
    return {
        ArtifactType.IMAGE: Artifact(
            id="d1:img", document_id="d1", type=ArtifactType.IMAGE, uri=str(path)
        )
    }


def test_honours_module_protocol() -> None:
    chain = BlockChainRecognizer(
        label="c0", recognizer=_FakeOCR("c0", "x"), corrector=_FakeCorrector("c0")
    )
    assert isinstance(chain, Module)
    assert chain.name == "block_chain:c0"
    assert chain.input_types == frozenset({ArtifactType.IMAGE})
    assert chain.output_types == frozenset({ArtifactType.RAW_TEXT})
    # La version compose celles des sous-modules (reproductibilité).
    assert "9.9" in chain.version and "1.1" in chain.version


def test_chains_ocr_then_correction_as_raw_text(tmp_path: Path) -> None:
    chain = BlockChainRecognizer(
        label="c0",
        recognizer=_FakeOCR("c0", "les manuscrits"),
        corrector=_FakeCorrector("c0"),
    )
    out = chain.execute(_image(tmp_path), {}, _ctx(tmp_path), RunControl())
    # Le fan-out lit un RAW_TEXT ; son contenu est le texte **corrigé**.
    raw = out.artifacts[ArtifactType.RAW_TEXT]
    assert raw.type == ArtifactType.RAW_TEXT
    assert raw.uri is not None
    assert Path(raw.uri).read_text(encoding="utf-8") == "LES MANUSCRITS"
    # Jetons des deux étapes sommés.
    assert out.usage is not None
    assert out.usage.tokens_in == 3 and out.usage.tokens_out == 5


def test_construction_rejects_bad_recognizer_contract() -> None:
    # Un « recognizer » qui lit du RAW_TEXT (pas une IMAGE) ne peut pas OCRiser
    # un bloc → refusé à la construction (échec tôt, pas au run).
    with pytest.raises(AdapterStepError, match="ne lit pas d'IMAGE"):
        BlockChainRecognizer(
            label="c0",
            recognizer=_FakeCorrector("c0"),
            corrector=_FakeCorrector("c0"),
        )


def test_construction_rejects_bad_corrector_contract() -> None:
    # Un « correcteur » qui lit une IMAGE (pas du RAW_TEXT) n'est pas un LLM
    # texte de post-correction → refusé à la construction.
    with pytest.raises(AdapterStepError, match="ne lit pas de RAW_TEXT"):
        BlockChainRecognizer(
            label="c0",
            recognizer=_FakeOCR("c0", "x"),
            corrector=_FakeOCR("c0", "x"),
        )
