"""Section bascule de classement : bump chart du rang moteur par métrique."""

from __future__ import annotations

from datetime import UTC, datetime

from xerocr.domain.run import RunManifest
from xerocr.evaluation.result import MetricScore, PipelineResult, RunResult
from xerocr.reports.section import SectionContext
from xerocr.reports.sections.rank_bump import RankBumpSection

FIXED = datetime(2026, 1, 1, tzinfo=UTC)


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


def test_bump_renders_one_line_per_engine() -> None:
    # tesseract gagne CER/WER, pero gagne F1/recherche → classements croisés.
    result = _result(
        (
            _pipe("tesseract", {"cer": 0.1, "wer": 0.1, "bow_f1": 0.5,
                                "searchability": 0.5}),
            _pipe("pero", {"cer": 0.2, "wer": 0.2, "bow_f1": 0.9,
                           "searchability": 0.9}),
        )
    )
    html = RankBumpSection().render(result, SectionContext())
    assert html is not None
    assert "bump-svg" in html
    assert html.count('class="bump-line"') == 2  # une ligne par moteur
    assert "Bascule de classement" in html
    assert "tesseract" in html and "pero" in html


def test_none_with_single_engine() -> None:
    result = _result(
        (_pipe("tesseract", {"cer": 0.1, "wer": 0.1, "bow_f1": 0.5}),)
    )
    assert RankBumpSection().render(result, SectionContext()) is None


def test_none_with_too_few_metrics() -> None:
    # une seule métrique partagée (< 2) → pas de bascule.
    result = _result((_pipe("a", {"cer": 0.1}), _pipe("b", {"cer": 0.2})))
    assert RankBumpSection().render(result, SectionContext()) is None
