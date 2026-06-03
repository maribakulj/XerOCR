"""Section synthèse : verdict factuel (meilleur pipeline · Δ CER · significativité).

Tous les nombres rendus sont une fonction auditable du ``RunResult`` (minimum,
soustraction, p-value) — pas de prose générée.
"""

from __future__ import annotations

from datetime import UTC, datetime

from xerocr.domain.run import RunManifest
from xerocr.evaluation.result import MetricScore, PipelineResult, RunResult
from xerocr.reports.section import Section, SectionContext
from xerocr.reports.sections.synthesis import SynthesisSection

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


def _pipeline(name: str, view: str, cer: float | None) -> PipelineResult:
    return PipelineResult(
        pipeline=name,
        view=view,
        aggregate=(MetricScore(metric="cer", value=cer, support=2),),
    )


def _result(
    pipelines: tuple[PipelineResult, ...],
    cross_engine: tuple[MetricScore, ...] = (),
) -> RunResult:
    return RunResult(
        manifest=_manifest(), pipelines=pipelines, cross_engine=cross_engine
    )


def test_satisfies_section_protocol() -> None:
    section = SynthesisSection()
    assert isinstance(section, Section)
    assert section.name == "synthesis"
    assert section.requires == ("cer",)


def test_best_pipeline_delta_and_significance() -> None:
    result = _result(
        (_pipeline("tess", "text", 0.25), _pipeline("ollama", "text", 0.10)),
        cross_engine=(
            MetricScore(metric="text:cer:significance_p", value=0.03, support=2),
        ),
    )
    html = SynthesisSection().render(result, SectionContext())
    assert html is not None
    assert "Synthèse" in html
    # meilleur = CER minimal (0.10), pas l'ordre d'entrée
    assert ">ollama<" in html
    assert "0.1000" in html  # CER du meilleur
    assert "0.1500" in html  # Δ = 0.25 - 0.10 (fonction auditable)
    assert "significatif (p=0.0300)" in html  # p < 0,05


def test_non_significant_gap() -> None:
    result = _result(
        (_pipeline("a", "text", 0.10), _pipeline("b", "text", 0.20)),
        cross_engine=(
            MetricScore(metric="text:cer:significance_p", value=0.40, support=2),
        ),
    )
    html = SynthesisSection().render(result, SectionContext())
    assert html is not None
    assert "non sig. (p=0.4000)" in html


def test_single_pipeline_has_no_comparison() -> None:
    html = SynthesisSection().render(
        _result((_pipeline("solo", "text", 0.12),)), SectionContext()
    )
    assert html is not None
    assert "0.1200" in html
    # pas de 2ᵉ / Δ / significativité fabriqués
    assert html.count("—") >= 3


def test_tie_is_deterministic() -> None:
    # CER égaux → départage par nom (a avant b), Δ = 0.0000, stable
    pipes = (_pipeline("b", "text", 0.15), _pipeline("a", "text", 0.15))
    html = SynthesisSection().render(_result(pipes), SectionContext())
    assert html is not None
    assert SynthesisSection().render(_result(pipes), SectionContext()) == html
    # "a" départage l'égalité → cellule « meilleur » avant la cellule « 2ᵉ » (b)
    assert html.index(">a</td>") < html.index(">b</td>")
    assert "0.0000" in html  # Δ nul


def test_view_without_cer_is_skipped() -> None:
    # une vue dont aucun pipeline ne porte de CER → aucune ligne → None
    pipe = PipelineResult(
        pipeline="p",
        view="layout",
        aggregate=(MetricScore(metric="region_detection", value=0.5, support=2),),
    )
    assert SynthesisSection().render(_result((pipe,)), SectionContext()) is None
