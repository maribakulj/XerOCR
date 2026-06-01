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


def _pipe(name: str, value: float) -> PipelineResult:
    return PipelineResult(
        pipeline=name,
        view="text",
        aggregate=(MetricScore(metric="cer", value=value, support=2),),
    )


def _two(cer_a: float, cer_b: float) -> RunResult:
    manifest = RunManifest(
        run_id="r",
        corpus_name="demo",
        n_documents=2,
        code_version="1.0",
        started_at=FIXED,
        completed_at=FIXED,
    )
    return RunResult(
        manifest=manifest, pipelines=(_pipe("tesseract", cer_a), _pipe("pero", cer_b))
    )


def test_readouts_show_real_scope() -> None:
    html = OverviewSection().render(_two(0.1, 0.2), SectionContext())
    assert html is not None
    assert 'class="readouts"' in html and 'class="readout"' in html
    # portée **réelle** : 2 documents, 2 pipelines, 1 vue, 1 métrique
    for label in ("Documents", "Pipelines", "Vues", "Métriques"):
        assert label in html


def test_data_bars_are_relative_to_column_max() -> None:
    html = OverviewSection().render(_two(0.1, 0.2), SectionContext())
    assert html is not None
    # cer 0.1 vs max 0.2 → 50 % ; 0.2 → 100 % (échelle relative à la colonne)
    assert 'class="db-fill" style="width:50%"' in html
    assert 'class="db-fill" style="width:100%"' in html
