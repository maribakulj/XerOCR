"""``RunSpec`` : composition déclarative, au moins un pipeline."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from xerocr.domain.artifacts import ArtifactType
from xerocr.domain.corpus import CorpusSpec
from xerocr.domain.evaluation import EvaluationSpec
from xerocr.domain.pipeline import PipelineSpec
from xerocr.domain.run_spec import RunSpec


def test_valid_runspec() -> None:
    spec = RunSpec(
        corpus=CorpusSpec(name="c"),
        pipelines=(PipelineSpec(name="p", initial_inputs=(ArtifactType.IMAGE,)),),
        evaluation=EvaluationSpec(),
    )
    assert spec.run_id is None
    assert len(spec.pipelines) == 1
    assert spec.adapter_kwargs == {}


def test_requires_at_least_one_pipeline() -> None:
    with pytest.raises(ValidationError):
        RunSpec(
            corpus=CorpusSpec(name="c"),
            pipelines=(),
            evaluation=EvaluationSpec(),
        )
