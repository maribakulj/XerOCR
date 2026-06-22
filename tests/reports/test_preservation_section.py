"""Section « Signaux patrimoniaux » (T5) : taux de préservation patrimoniale par
moteur, en faits mesurés (critère affiché, aucun verdict), gatée sur la présence
réelle d'au moins une mesure patrimoniale."""

from __future__ import annotations

from datetime import UTC, datetime

from xerocr.domain.run import RunManifest
from xerocr.evaluation.result import MetricScore, PipelineResult, RunResult
from xerocr.reports.section import SectionContext
from xerocr.reports.sections.preservation import PreservationSection

FIXED = datetime(2026, 1, 1, tzinfo=UTC)


def _result(pipelines: tuple[PipelineResult, ...]) -> RunResult:
    manifest = RunManifest(
        run_id="r", corpus_name="c", n_documents=1, code_version="1.0",
        started_at=FIXED, completed_at=FIXED,
    )
    return RunResult(manifest=manifest, pipelines=pipelines, documents=(), analyses=())


def _pipe(name: str, **scores: float) -> PipelineResult:
    agg = tuple(MetricScore(metric=k, value=v, support=1) for k, v in scores.items())
    return PipelineResult(pipeline=name, view="text", aggregate=agg)


def test_renders_present_signals_with_criterion_and_direction() -> None:
    res = _result((
        _pipe("tesseract", cer=0.13, diacritic_err=0.08, hcpr=0.91),
        _pipe("kraken", cer=0.10, diacritic_err=0.04, hcpr=0.95),
    ))
    html = PreservationSection().render(res, SectionContext())
    assert html is not None
    # titre patrimonial + valeurs présentes en pourcentage.
    assert "Signaux patrimoniaux" in html
    assert "8.0%" in html and "91.0%" in html
    # critère exact (fait mesuré) + sens de lecture + neutralité.
    assert "diacritiques de la vérité terrain mal restitués" in html
    assert "↓" in html and "↑" in html
    assert "aucun gagnant n'est déclaré" in html.lower()


def test_absent_signals_render_nothing() -> None:
    # un run texte-seul sans aucune métrique patrimoniale → pas de section vide.
    res = _result((_pipe("tesseract", cer=0.13, wer=0.2),))
    assert PreservationSection().render(res, SectionContext()) is None


def test_only_present_columns_are_shown() -> None:
    # mufi_err / air absents → leurs colonnes ne doivent pas apparaître.
    res = _result((_pipe("tesseract", cer=0.13, diacritic_err=0.08),))
    html = PreservationSection().render(res, SectionContext())
    assert html is not None
    assert "Erreur diacritiques" in html
    assert "MUFI" not in html and "AIR" not in html


def test_no_pipelines_render_nothing() -> None:
    assert PreservationSection().render(_result(()), SectionContext()) is None
