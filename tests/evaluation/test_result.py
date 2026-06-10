"""``RunResult`` : sérialisation déterministe (golden octet-stable)."""

from __future__ import annotations

from datetime import UTC, datetime

from xerocr.domain.run import RunManifest
from xerocr.domain.usage import ResourceUsage
from xerocr.evaluation.result import (
    DocumentUsage,
    MetricScore,
    PipelineResult,
    RunResult,
)


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
    assert result.schema_version == 2
    blob = result.model_dump_json().replace(" ", "")
    assert '"metric":"cer"' in blob
    assert '"support":1' in blob


def test_usage_channel_round_trips() -> None:
    result = RunResult(
        manifest=_manifest(),
        usage=(
            DocumentUsage(
                document_id="d1",
                pipeline="p",
                usage=ResourceUsage(
                    duration_seconds=1.5, tokens_in=100, tokens_out=40
                ),
            ),
        ),
    )
    reloaded = RunResult.model_validate_json(result.model_dump_json())
    assert reloaded.usage[0].usage.tokens_out == 40
    assert reloaded.usage[0].usage.duration_seconds == 1.5


def test_v1_payload_without_usage_still_loads() -> None:
    blob = _result().model_dump_json()
    stripped = blob.replace(',"usage":[]', "")
    assert '"usage"' not in stripped
    reloaded = RunResult.model_validate_json(stripped)
    assert reloaded.usage == ()
