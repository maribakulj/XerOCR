"""``compare_runs`` (deltas) + ``render_comparison`` (rapport autonome)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from xerocr.domain.run import RunManifest
from xerocr.evaluation.result import MetricScore, PipelineResult, RunResult
from xerocr.reports.compare import compare_runs, render_comparison

FIXED = datetime(2026, 1, 1, tzinfo=UTC)


def _result(run_id: str, cer: float | None) -> RunResult:
    manifest = RunManifest(
        run_id=run_id,
        corpus_name="c",
        n_documents=1,
        code_version="1.0",
        started_at=FIXED,
        completed_at=FIXED,
    )
    return RunResult(
        manifest=manifest,
        pipelines=(
            PipelineResult(
                pipeline="eng",
                view="text",
                aggregate=(MetricScore(metric="cer", value=cer, support=1),),
            ),
        ),
    )


def test_delta_computed() -> None:
    deltas = compare_runs(_result("A", 0.30), _result("B", 0.25))
    assert len(deltas) == 1
    delta = deltas[0]
    assert (delta.pipeline, delta.view, delta.metric) == ("eng", "text", "cer")
    assert delta.value_a == 0.30
    assert delta.value_b == 0.25
    assert delta.delta == pytest.approx(-0.05)


def test_delta_none_when_value_missing() -> None:
    deltas = compare_runs(_result("A", 0.30), _result("B", None))
    assert deltas[0].delta is None


def test_render_comparison_is_autonomous_html() -> None:
    html = render_comparison(_result("A", 0.30), _result("B", 0.25))
    assert html.startswith("<!DOCTYPE html>")
    assert "comparaison" in html.lower()
    assert "-0.0500" in html
