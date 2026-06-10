"""Renderer : structure du document, déterminisme, no-orphan."""

from __future__ import annotations

from datetime import UTC, datetime

from xerocr.domain.run import RunManifest
from xerocr.evaluation.result import MetricScore, PipelineResult, RunResult
from xerocr.reports.renderer import ReportRenderer, default_report_renderer
from xerocr.reports.section import Html, SectionContext

FIXED = datetime(2026, 1, 1, tzinfo=UTC)


def _result() -> RunResult:
    manifest = RunManifest(
        run_id="r",
        corpus_name="demo",
        n_documents=1,
        code_version="1.0",
        started_at=FIXED,
        completed_at=FIXED,
    )
    return RunResult(
        manifest=manifest,
        pipelines=(
            PipelineResult(
                pipeline="p",
                view="text",
                aggregate=(MetricScore(metric="cer", value=0.1, support=1),),
            ),
        ),
    )


def test_document_structure_and_determinism() -> None:
    renderer = default_report_renderer()
    html1 = renderer.render(_result())
    html2 = renderer.render(_result())
    assert html1 == html2  # octet-stable
    assert html1.startswith("<!DOCTYPE html>")
    assert "<title>" in html1
    assert "</html>" in html1
    # S4.a : le rapport porte le chrome au design (carte gris chaud + en-tête pilule)
    assert 'class="report-board"' in html1
    assert 'class="report-chrome"' in html1
    assert 'class="sec"' in html1
    # trame de points (halftone Xerox) en fond, via data: URI inline
    assert "data:image/svg+xml" in html1 and "fill-opacity" in html1
    # 3a : widget « comparer un run » (client-side) en pied de rapport.
    assert 'id="xerocr-compare-btn"' in html1
    # 3a : badge moteur (lettre + accent) devant le nom du moteur.
    assert 'class="eng-badge"' in html1
    # autonome : aucune ressource externe (ni @import, ni CDN https, ni <link>)
    assert "@import" not in html1
    assert "https://" not in html1
    assert "<link" not in html1


class _NeedsWer:
    name = "wer_section"
    requires = ("wer",)

    def render(self, result: RunResult, ctx: SectionContext) -> Html:
        return Html("<p>WER</p>")


class _Always:
    name = "always"
    requires: tuple[str, ...] = ()

    def render(self, result: RunResult, ctx: SectionContext) -> Html:
        return Html("<p>ALWAYS</p>")


def test_no_orphan_skips_section_with_unmet_requires() -> None:
    html = ReportRenderer((_NeedsWer(), _Always())).render(_result())
    # On vérifie le **markup** rendu, pas une sous-chaîne nue : depuis que le
    # rapport incorpore ses polices (base64), "WER"/"ALWAYS" apparaissent par
    # hasard dans le data-URI. "<p>…</p>" ne peut pas (pas de "<" en base64).
    assert "<p>ALWAYS</p>" in html  # requires=() rendu
    assert "<p>WER</p>" not in html  # requires=("wer",) sauté (seul cer présent)
