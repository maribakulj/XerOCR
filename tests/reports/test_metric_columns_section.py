"""Section colonnes métriques : comparatif moteur en colonnes groupées."""

from __future__ import annotations

from datetime import UTC, datetime

from xerocr.domain.run import RunManifest
from xerocr.evaluation.result import MetricScore, PipelineResult, RunResult
from xerocr.reports.section import SectionContext
from xerocr.reports.sections.metric_columns import MetricColumnsSection

FIXED = datetime(2026, 1, 1, tzinfo=UTC)
_METRICS = ("char_accuracy", "word_accuracy", "bow_f1", "searchability")


def _pipe(name: str, values: dict[str, float]) -> PipelineResult:
    return PipelineResult(
        pipeline=name,
        view="text",
        aggregate=tuple(
            MetricScore(metric=m, value=v, support=2) for m, v in values.items()
        ),
    )


def _result(pipelines: tuple[PipelineResult, ...]) -> RunResult:
    manifest = RunManifest(
        run_id="r", corpus_name="demo", n_documents=2,
        code_version="1.0", started_at=FIXED, completed_at=FIXED,
    )
    return RunResult(manifest=manifest, pipelines=pipelines, documents=())


def test_columns_one_bar_per_metric_and_engine() -> None:
    full = {m: 0.8 for m in _METRICS}
    result = _result((_pipe("tesseract", full), _pipe("pero", dict(full, bow_f1=0.5))))
    html = MetricColumnsSection().render(result, SectionContext())
    assert html is not None
    assert "col-svg" in html
    assert html.count('class="col-bar"') == 8  # 4 métriques × 2 moteurs
    assert "Colonnes métriques" in html
    assert "tesseract" in html and "pero" in html


def test_none_when_no_shared_accuracy_metric() -> None:
    result = _result((_pipe("tesseract", {"cer": 0.2}),))
    assert MetricColumnsSection().render(result, SectionContext()) is None


def test_none_without_pipelines() -> None:
    assert MetricColumnsSection().render(_result(()), SectionContext()) is None
