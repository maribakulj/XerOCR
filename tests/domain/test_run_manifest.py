from __future__ import annotations

from xerocr.domain import PipelineSpec, RunManifest, utcnow


def _make() -> RunManifest:
    t = utcnow()
    return RunManifest(
        run_id="r",
        corpus_name="c",
        n_documents=1,
        code_version="0.1.0",
        started_at=t,
        completed_at=t,
        pipeline_specs=(PipelineSpec(name="p"),),
    )


def test_no_pipeline_names_field():
    assert "pipeline_names" not in RunManifest.model_fields


def test_roundtrip_json_stable():
    m = _make()
    serialized = m.model_dump_json()
    reparsed = RunManifest.model_validate_json(serialized)
    assert reparsed.model_dump_json() == serialized


def test_duration_non_negative():
    assert _make().duration_seconds >= 0.0
