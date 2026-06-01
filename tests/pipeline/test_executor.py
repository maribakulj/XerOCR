"""``PipelineExecutor`` — résolution des entrées, estampillage, annulation."""

from __future__ import annotations

import pytest

from xerocr.domain.artifacts import Artifact, ArtifactType
from xerocr.domain.errors import RunCancelledError, XerOCRError
from xerocr.domain.pipeline import PipelineSpec, PipelineStep
from xerocr.pipeline.executor import PipelineExecutor, PipelineStepError
from xerocr.pipeline.run_control import RunControl

CODE_VERSION = "test-1.0"


def _image() -> Artifact:
    return Artifact(
        id="doc1:init:image",
        document_id="doc1",
        type=ArtifactType.IMAGE,
        uri="img://doc1.png",
    )


class _EchoModule:
    """Module de test : IMAGE → RAW_TEXT."""

    name = "fake:echo"
    version = "0.1"
    input_types = frozenset({ArtifactType.IMAGE})
    output_types = frozenset({ArtifactType.RAW_TEXT})

    def execute(self, inputs, params, context, control):  # noqa: ANN001, ANN201
        return {
            ArtifactType.RAW_TEXT: Artifact(
                id=f"{context.document_id}:{self.name}:raw_text",
                document_id=context.document_id,
                type=ArtifactType.RAW_TEXT,
                uri="mem://raw",
            )
        }


class _UpperModule:
    """Module de test : RAW_TEXT → CORRECTED_TEXT."""

    name = "fake:upper"
    version = "0.1"
    input_types = frozenset({ArtifactType.RAW_TEXT})
    output_types = frozenset({ArtifactType.CORRECTED_TEXT})

    def execute(self, inputs, params, context, control):  # noqa: ANN001, ANN201
        return {
            ArtifactType.CORRECTED_TEXT: Artifact(
                id=f"{context.document_id}:{self.name}:corrected",
                document_id=context.document_id,
                type=ArtifactType.CORRECTED_TEXT,
                uri="mem://corrected",
            )
        }


class _EmptyModule:
    """Module fautif : déclare RAW_TEXT mais ne produit rien."""

    name = "fake:empty"
    version = "0.1"
    input_types = frozenset({ArtifactType.IMAGE})
    output_types = frozenset({ArtifactType.RAW_TEXT})

    def execute(self, inputs, params, context, control):  # noqa: ANN001, ANN201
        return {}


def _ocr_step() -> PipelineStep:
    return PipelineStep(
        id="ocr",
        kind="ocr",
        adapter_name="fake:echo",
        input_types=(ArtifactType.IMAGE,),
        output_types=(ArtifactType.RAW_TEXT,),
    )


def test_runs_single_step_and_stamps_provenance() -> None:
    spec = PipelineSpec(
        name="p1", initial_inputs=(ArtifactType.IMAGE,), steps=(_ocr_step(),)
    )
    ex = PipelineExecutor(CODE_VERSION)
    pool = ex.execute_document(
        spec, {"fake:echo": _EchoModule()}, {ArtifactType.IMAGE: _image()},
        document_id="doc1",
    )
    art = pool[ArtifactType.RAW_TEXT]
    assert art.produced_by_step == "ocr"
    assert art.provenance is not None
    assert art.provenance.code_version == CODE_VERSION
    assert art.provenance.parameters_hash is not None


def test_two_steps_resolve_inputs_from() -> None:
    step2 = PipelineStep(
        id="llm",
        kind="post_correction",
        adapter_name="fake:upper",
        input_types=(ArtifactType.RAW_TEXT,),
        output_types=(ArtifactType.CORRECTED_TEXT,),
        inputs_from={ArtifactType.RAW_TEXT: "ocr"},
    )
    spec = PipelineSpec(
        name="p2", initial_inputs=(ArtifactType.IMAGE,), steps=(_ocr_step(), step2)
    )
    ex = PipelineExecutor(CODE_VERSION)
    pool = ex.execute_document(
        spec,
        {"fake:echo": _EchoModule(), "fake:upper": _UpperModule()},
        {ArtifactType.IMAGE: _image()},
        document_id="doc1",
    )
    assert ArtifactType.CORRECTED_TEXT in pool


def test_missing_module_raises() -> None:
    spec = PipelineSpec(
        name="p1", initial_inputs=(ArtifactType.IMAGE,), steps=(_ocr_step(),)
    )
    ex = PipelineExecutor(CODE_VERSION)
    with pytest.raises(PipelineStepError):
        ex.execute_document(
            spec, {}, {ArtifactType.IMAGE: _image()}, document_id="doc1"
        )


def test_missing_input_raises() -> None:
    spec = PipelineSpec(
        name="p1", initial_inputs=(ArtifactType.IMAGE,), steps=(_ocr_step(),)
    )
    ex = PipelineExecutor(CODE_VERSION)
    with pytest.raises(PipelineStepError):
        ex.execute_document(
            spec, {"fake:echo": _EchoModule()}, {}, document_id="doc1"
        )


def test_undeclared_output_raises() -> None:
    bad = PipelineStep(
        id="bad",
        kind="ocr",
        adapter_name="fake:empty",
        input_types=(ArtifactType.IMAGE,),
        output_types=(ArtifactType.RAW_TEXT,),
    )
    spec = PipelineSpec(
        name="pbad", initial_inputs=(ArtifactType.IMAGE,), steps=(bad,)
    )
    ex = PipelineExecutor(CODE_VERSION)
    with pytest.raises(PipelineStepError):
        ex.execute_document(
            spec, {"fake:empty": _EmptyModule()}, {ArtifactType.IMAGE: _image()},
            document_id="doc1",
        )


def test_cancellation_raises_before_step() -> None:
    spec = PipelineSpec(
        name="p1", initial_inputs=(ArtifactType.IMAGE,), steps=(_ocr_step(),)
    )
    ex = PipelineExecutor(CODE_VERSION)
    control = RunControl()
    control.trigger_cancel()
    with pytest.raises(RunCancelledError):
        ex.execute_document(
            spec, {"fake:echo": _EchoModule()}, {ArtifactType.IMAGE: _image()},
            document_id="doc1", control=control,
        )


def test_empty_code_version_rejected() -> None:
    with pytest.raises(XerOCRError):
        PipelineExecutor("")


def test_threads_workspace_uri_to_context() -> None:
    captured: dict[str, str | None] = {}

    class _Capture:
        input_types = frozenset({ArtifactType.IMAGE})
        output_types = frozenset({ArtifactType.RAW_TEXT})

        def execute(self, inputs, params, context, control):  # noqa: ANN001, ANN201
            captured["workspace"] = context.workspace_uri
            return {
                ArtifactType.RAW_TEXT: Artifact(
                    id=f"{context.document_id}:cap:raw_text",
                    document_id=context.document_id,
                    type=ArtifactType.RAW_TEXT,
                    uri="mem://x",
                )
            }

    spec = PipelineSpec(
        name="p", initial_inputs=(ArtifactType.IMAGE,), steps=(_ocr_step(),)
    )
    PipelineExecutor(CODE_VERSION).execute_document(
        spec,
        {"fake:echo": _Capture()},
        {ArtifactType.IMAGE: _image()},
        document_id="doc1",
        workspace_uri="/work",
    )
    assert captured["workspace"] == "/work"
