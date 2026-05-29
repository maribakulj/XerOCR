from __future__ import annotations

from xerocr.domain import (
    ArtifactType,
    EvaluationSpec,
    EvaluationView,
    MetricSpec,
    ProjectionSpec,
)


def test_metric_spec_is_declarative():
    assert "func" not in MetricSpec.model_fields
    m = MetricSpec(
        name="cer", input_types=(ArtifactType.RAW_TEXT, ArtifactType.RAW_TEXT),
    )
    assert m.higher_is_better is False


def test_view_accepts():
    v = EvaluationView(name="text", candidate_types=frozenset({ArtifactType.RAW_TEXT}))
    assert v.accepts(ArtifactType.RAW_TEXT)
    assert not v.accepts(ArtifactType.ALTO_XML)


def test_projection_for_resolution():
    proj = ProjectionSpec(
        source_type=ArtifactType.ALTO_XML,
        target_type=ArtifactType.RAW_TEXT,
        projector_name="alto_to_text",
    )
    v = EvaluationView(
        name="text",
        candidate_types=frozenset({ArtifactType.RAW_TEXT, ArtifactType.ALTO_XML}),
        projection=proj,
    )
    assert v.projection_for(ArtifactType.ALTO_XML) is proj
    assert v.projection_for(ArtifactType.RAW_TEXT) is None


def test_spec_view_lookup():
    v = EvaluationView(name="text", candidate_types=frozenset({ArtifactType.RAW_TEXT}))
    spec = EvaluationSpec(views=(v,))
    assert spec.view_by_name("text") is v
    assert spec.view_by_name("x") is None
