from __future__ import annotations

import typing

import pytest

from xerocr.domain import (
    INITIAL_STEP_ID,
    ArtifactType,
    PipelineMode,
    PipelineSpec,
    PipelineStep,
)
from xerocr.domain.errors import XerOCRError


def test_pipeline_mode_values():
    assert set(typing.get_args(PipelineMode)) == {
        "text_only",
        "text_and_image",
        "zero_shot",
    }


def test_reserved_step_id_rejected():
    with pytest.raises(XerOCRError):
        PipelineStep(id=INITIAL_STEP_ID, kind="ocr", adapter_name="t")


def test_bad_step_id_rejected():
    with pytest.raises(XerOCRError):
        PipelineStep(id="bad id", kind="ocr", adapter_name="t")


def test_spec_step_lookup():
    step = PipelineStep(
        id="ocr", kind="ocr", adapter_name="t",
        output_types=(ArtifactType.RAW_TEXT,),
    )
    spec = PipelineSpec(name="p", steps=(step,))
    assert spec.step_by_id("ocr") is step
    assert spec.step_by_id("x") is None
