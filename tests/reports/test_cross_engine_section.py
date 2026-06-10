"""Section cross_engine : clé parsée en colonnes + verdict, ``None`` si absent."""

from __future__ import annotations

from datetime import UTC, datetime

from xerocr.domain.run import RunManifest
from xerocr.evaluation.analysis import (
    Analysis,
    InferencePayload,
    PipelineInterval,
    PipelineRank,
)
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


def test_inference_block_renders_ranks_cd_and_intervals() -> None:
    payload = InferencePayload(
        metric="cer",
        alpha=0.05,
        n_documents=8,
        critical_distance=1.1715,
        q_alpha=2.343,
        mean_ranks=(
            PipelineRank(pipeline="alpha", mean_rank=1.375),
            PipelineRank(pipeline="beta", mean_rank=3.0),
        ),
        tied_groups=(("alpha",), ("beta",)),
        intervals=(
            PipelineInterval(
                pipeline="alpha", mean=0.1062, lower=0.095, upper=0.1162,
                n_documents=8,
            ),
        ),
    )
    result = RunResult(
        manifest=_manifest(),
        cross_engine=(
            MetricScore(metric="text:cer:significance_p", value=0.01, support=8),
        ),
        analyses=(Analysis(scope="corpus", view="text", payload=payload),),
    )
    html = CrossEngineSection().render(result, SectionContext())
    assert html is not None
    assert "CD = 1.1715" in html
    assert "rang moyen" in html
    assert "[0.0950 ; 0.1162]" in html
    assert "{alpha}" in html and "{beta}" in html
    # Déterminisme bit-à-bit du rendu.
    assert html == CrossEngineSection().render(result, SectionContext())


def test_two_pipeline_inference_block_points_to_wilcoxon() -> None:
    payload = InferencePayload(
        metric="cer",
        alpha=0.05,
        n_documents=8,
        mean_ranks=(
            PipelineRank(pipeline="alpha", mean_rank=1.0),
            PipelineRank(pipeline="beta", mean_rank=2.0),
        ),
    )
    result = RunResult(
        manifest=_manifest(),
        cross_engine=(
            MetricScore(metric="text:cer:significance_p", value=0.02, support=8),
        ),
        analyses=(Analysis(scope="corpus", view="text", payload=payload),),
    )
    html = CrossEngineSection().render(result, SectionContext())
    assert html is not None
    assert "pas de post-hoc" in html
