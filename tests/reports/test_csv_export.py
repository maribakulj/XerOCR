"""Export CSV : lecture pure du RunResult, ordre et valeurs exactes."""

from __future__ import annotations

from datetime import UTC, datetime

from xerocr.domain.run import RunManifest
from xerocr.evaluation.result import (
    MetricScore,
    PipelineResult,
    RunDocumentResult,
    RunResult,
)
from xerocr.reports.csv_export import run_result_csv

FIXED = datetime(2026, 6, 1, tzinfo=UTC)


def _result() -> RunResult:
    manifest = RunManifest(
        run_id="r", corpus_name="c", n_documents=1,
        code_version="1.0", started_at=FIXED, completed_at=FIXED,
    )
    return RunResult(
        manifest=manifest,
        pipelines=(
            PipelineResult(
                pipeline="tess", view="text",
                aggregate=(MetricScore(metric="cer", value=0.25, support=1),),
            ),
        ),
        documents=(
            RunDocumentResult(
                document_id="d1", pipeline="tess", view="text",
                scores=(
                    MetricScore(metric="cer", value=0.25, support=4),
                    MetricScore(metric="wer", value=None, support=None),
                ),
            ),
        ),
    )


def test_csv_exact_content() -> None:
    assert run_result_csv(_result()) == (
        "scope,view,pipeline,document_id,metric,value,support\n"
        "aggregate,text,tess,,cer,0.25,1\n"
        "document,text,tess,d1,cer,0.25,4\n"
        "document,text,tess,d1,wer,,\n"
    )


def test_csv_is_deterministic() -> None:
    assert run_result_csv(_result()) == run_result_csv(_result())
