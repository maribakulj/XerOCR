"""Section cross_engine : clé parsée en colonnes + verdict, ``None`` si absent."""

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


def _result(metric: str, value: float | None) -> RunResult:
    return RunResult(
        manifest=_manifest(),
        cross_engine=(MetricScore(metric=metric, value=value, support=10),),
    )


def test_significant_verdict_and_parsed_columns() -> None:
    html = CrossEngineSection().render(
        _result("text:cer:significance_p", 0.03), SectionContext()
    )
    assert html is not None
    assert "Significativité" in html
    # clé éclatée en colonnes Vue / Métrique
    assert ">text<" in html and ">cer<" in html
    assert "0.0300" in html
    assert "significatif" in html  # p=0,03 < 0,05


def test_non_significant_verdict() -> None:
    html = CrossEngineSection().render(
        _result("text:cer:significance_p", 0.20), SectionContext()
    )
    assert html is not None
    assert "non sig." in html  # p=0,20 ≥ 0,05


def test_none_value_rendered_as_dash() -> None:
    html = CrossEngineSection().render(_result("x", None), SectionContext())
    assert html is not None
    assert "—" in html


def test_empty_cross_engine_returns_none() -> None:
    section = CrossEngineSection()
    assert section.render(RunResult(manifest=_manifest()), SectionContext()) is None
