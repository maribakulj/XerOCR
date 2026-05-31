"""``RunResult`` : sérialisation déterministe (golden octet-stable)."""

from __future__ import annotations

from datetime import UTC, datetime

from xerocr.domain.run import RunManifest
from xerocr.evaluation.result import MetricScore, PipelineResult, RunResult


def _manifest() -> RunManifest:
    fixed = datetime(2026, 1, 1, tzinfo=UTC)
    return RunManifest(
        run_id="demo",
        corpus_name="demo",
        n_documents=1,
        code_version="1.0",
        started_at=fixed,
        completed_at=fixed,
    )


def _result() -> RunResult:
    return RunResult(
        manifest=_manifest(),
        pipelines=(
            PipelineResult(
                pipeline="p",
                view="text",
                aggregate=(MetricScore(metric="cer", value=0.25, support=1),),
            ),
        ),
    )


def test_serialisation_is_deterministic() -> None:
    assert _result().model_dump_json() == _result().model_dump_json()


def test_schema_version_and_stable_keys() -> None:
    result = _result()
    assert result.schema_version == 1
    blob = result.model_dump_json().replace(" ", "")
    assert '"metric":"cer"' in blob
    assert '"support":1' in blob
