"""Section lines : distribution + heatmap rendues, ``None`` sans payload."""

from __future__ import annotations

from datetime import UTC, datetime

from xerocr.domain.run import RunManifest
from xerocr.evaluation.analysis import (
    Analysis,
    CatastrophicRate,
    LinePercentiles,
    LinesPayload,
    PipelineLines,
)
from xerocr.evaluation.result import RunResult
from xerocr.reports.section import SectionContext
from xerocr.reports.sections.lines import LinesSection

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


def _result() -> RunResult:
    payload = LinesPayload(
        heatmap_bins=10,
        pipelines=(
            PipelineLines(
                pipeline="alpha",
                line_count=5,
                mean_cer=0.44,
                gini=0.436,
                percentiles=LinePercentiles(
                    p50=0.4, p75=0.6, p90=0.84, p95=0.92, p99=0.984
                ),
                catastrophic=(
                    CatastrophicRate(threshold=0.30, count=3, rate=0.6),
                    CatastrophicRate(threshold=0.50, count=2, rate=0.4),
                    CatastrophicRate(threshold=1.00, count=1, rate=0.2),
                ),
                heatmap=(0.0, None, 0.2, None, 0.4, None, 0.6, None, 1.0, None),
            ),
        ),
    )
    return RunResult(
        manifest=_manifest(),
        analyses=(Analysis(scope="corpus", view="text", payload=payload),),
    )


def test_distribution_and_heatmap_render() -> None:
    html = LinesSection().render(_result(), SectionContext())
    assert html is not None
    assert "Distribution des erreurs par ligne" in html
    assert "alpha" in html
    assert "44.0%" in html  # CER moyen
    assert "98.4%" in html  # p99
    assert "0.436" in html  # Gini
    assert "≥0.30 : 60.0%" in html  # taux catastrophique, seuil inclusif
    assert "heatmap" in html
    assert "—" in html  # tranche sans ligne : tiret, jamais un faux zéro
    # Déterminisme bit-à-bit du rendu.
    assert html == LinesSection().render(_result(), SectionContext())


def test_renders_english_labels() -> None:
    html = LinesSection().render(_result(), SectionContext(lang="en"))
    assert html is not None
    assert "Per-line error distribution" in html
    assert "Distribution des erreurs par ligne" not in html
    assert "per-line CER distribution" in html
    assert "distribution du CER par ligne" not in html
    assert "mean CER" in html and "CER moyen" not in html
    assert "catastrophic" in html and "catastrophiques" not in html


def test_no_payload_returns_none() -> None:
    section = LinesSection()
    assert section.render(RunResult(manifest=_manifest()), SectionContext()) is None
