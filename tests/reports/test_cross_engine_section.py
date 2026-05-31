"""Section cross_engine : rend les significativités, ``None`` si absent."""

from __future__ import annotations

from datetime import UTC, datetime

from xerocr.domain.run import RunManifest
from xerocr.evaluation.result import MetricScore, RunResult
from xerocr.reports.section import SectionContext
from xerocr.reports.sections.cross_engine import CrossEngineSection

FIXED = datetime(2026, 1, 1, tzinfo=UTC)


def _manifest() -> RunManifest:
    return RunManifest(
        run_id="r",
        corpus_name="c",
        n_documents=2,
        code_version="1.0",
        started_at=FIXED,
        completed_at=FIXED,
    )


def test_renders_significance() -> None:
    result = RunResult(
        manifest=_manifest(),
        cross_engine=(
            MetricScore(metric="text:cer:significance_p", value=0.03, support=10),
        ),
    )
    html = CrossEngineSection().render(result, SectionContext())
    assert html is not None
    assert "text:cer:significance_p" in html
    assert "0.0300" in html
    assert "Significativité" in html


def test_none_value_rendered_as_dash() -> None:
    result = RunResult(
        manifest=_manifest(),
        cross_engine=(MetricScore(metric="x", value=None, support=1),),
    )
    html = CrossEngineSection().render(result, SectionContext())
    assert html is not None
    assert "—" in html


def test_empty_cross_engine_returns_none() -> None:
    section = CrossEngineSection()
    assert section.render(RunResult(manifest=_manifest()), SectionContext()) is None
