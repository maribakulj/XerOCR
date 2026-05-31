"""Section overview : tableau, valeurs, ``None`` → tiret, résultat vide."""

from __future__ import annotations

from datetime import UTC, datetime

from xerocr.domain.run import RunManifest
from xerocr.evaluation.result import MetricScore, PipelineResult, RunResult
from xerocr.reports.section import SectionContext
from xerocr.reports.sections.overview import OverviewSection

FIXED = datetime(2026, 1, 1, tzinfo=UTC)


def _result(value: float | None) -> RunResult:
    manifest = RunManifest(
        run_id="r",
        corpus_name="demo",
        n_documents=2,
        code_version="1.0",
        started_at=FIXED,
        completed_at=FIXED,
    )
    return RunResult(
        manifest=manifest,
        pipelines=(
            PipelineResult(
                pipeline="tesseract",
                view="text",
                aggregate=(MetricScore(metric="cer", value=value, support=2),),
            ),
        ),
    )


def test_renders_table_with_values() -> None:
    html = OverviewSection().render(_result(0.25), SectionContext())
    assert html is not None
    assert "tesseract" in html
    assert "0.2500" in html
    assert "demo" in html
    assert "cer" in html


def test_none_value_rendered_as_dash() -> None:
    html = OverviewSection().render(_result(None), SectionContext())
    assert html is not None
    assert "—" in html


def test_empty_result_returns_none() -> None:
    manifest = RunManifest(
        run_id="r",
        corpus_name="c",
        n_documents=0,
        code_version="1.0",
        started_at=FIXED,
        completed_at=FIXED,
    )
    section = OverviewSection()
    assert section.render(RunResult(manifest=manifest), SectionContext()) is None
