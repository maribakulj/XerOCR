"""``RunSpec`` : composition déclarative, au moins un pipeline."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from cinoc.domain.artifacts import ArtifactType
from cinoc.domain.corpus import CorpusSpec
from cinoc.domain.evaluation import EvaluationSpec
from cinoc.domain.pipeline import PipelineSpec
from cinoc.domain.run_spec import RunSpec


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
