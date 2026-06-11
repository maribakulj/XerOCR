"""``ReportRenderer`` — compose des sections en un document HTML autonome.

**Injecté par l'``app``** (reports ne connaît pas app) : ``app`` choisit les
sections. ``default_report_renderer`` fournit le socle (overview) du squelette.
"""

from __future__ import annotations

from xerocr.evaluation.result import RunResult
from xerocr.reports.compare_widget import compare_widget
from xerocr.reports.embedded import inline_script
from xerocr.reports.html import escape, render_document
from xerocr.reports.section import Html, Section, SectionContext

#: Libellés FR des sections pour le sommaire (deeplinks) ; repli = nom brut.
_SECTION_LABELS = {
    "synthesis": "Synthèse",
    "overview": "Vue d'ensemble",
    "by_engine": "Par moteur",
    "by_document": "Par document",
    "documents_gallery": "Galerie",
    "cross_engine": "Inter-moteurs",
    "economics": "Économie",
    "diagnostics": "Diagnostic",
    "taxonomy": "Taxonomie",
    "calibration": "Calibration",
    "glossary": "Glossaire",
}


def _label(name: str) -> str:
    return _SECTION_LABELS.get(name, name)


def _toc_nav(names: list[str]) -> str:
    """Sommaire **deeplinkable** (ancres natives, zéro JS) + landmark ARIA.

    Affiché dès qu'il y a ≥ 2 sections (un sommaire d'une entrée est inutile)."""
    if len(names) < 2:
        return ""
    links = "".join(
        f'<a href="#r-{escape(name)}">{escape(_label(name))}</a>' for name in names
    )
    return (
        '<nav class="report-toc" aria-label="Sommaire du rapport">' f"{links}</nav>"
    )


class ReportRenderer:
    """Assemble les sections applicables en un rapport HTML."""

    def __init__(self, sections: tuple[Section, ...]) -> None:
        self._sections = sections

    def render(
        self,
        result: RunResult,
        *,
        title: str = "XerOCR — rapport",
        lang: str = "fr",
    ) -> str:
        known = {
            score.metric
            for pipeline in result.pipelines
            for score in pipeline.aggregate
        }
        ctx = SectionContext(title=title, lang=lang)
        rendered: list[tuple[str, str]] = []
        for section in self._sections:
            if section.requires and not set(section.requires) <= known:
                continue  # no-orphan : métriques requises absentes
            html = section.render(result, ctx)
            if html is not None:
                rendered.append((section.name, html))
        # Chaque section devient une **région** ancrée (deeplink #r-<name> + ARIA) ;
        # un sommaire en tête relie les régions (navigation native, sans JS).
        nav = _toc_nav([name for name, _ in rendered])
        blocks = "".join(
            f'<section id="r-{escape(name)}" class="r-block" '
            f'aria-label="{escape(_label(name))}">{html}</section>'
            for name, html in rendered
        )
        # Pied : widget « comparer un run » + script d'interactivité (navigation
        # clavier + palette). Tous deux client-side, déterministes, inlinés.
        footer = Html(compare_widget(result) + inline_script("report.js"))
        return render_document(title, Html(nav + blocks), footer=footer, lang=lang)


def default_report_renderer() -> ReportRenderer:
    """Socle : synthèse, overview, par-moteur/document, stats, économie,
    diagnostic, glossaire pédagogique."""
    from xerocr.reports.sections.by_document import DocumentSection
    from xerocr.reports.sections.by_engine import EngineSection
    from xerocr.reports.sections.calibration import CalibrationSection
    from xerocr.reports.sections.cross_engine import CrossEngineSection
    from xerocr.reports.sections.diagnostics import DiagnosticsSection
    from xerocr.reports.sections.economics import EconomicsSection
    from xerocr.reports.sections.gallery import DocumentGallerySection
    from xerocr.reports.sections.glossary import GlossarySection
    from xerocr.reports.sections.overview import OverviewSection
    from xerocr.reports.sections.synthesis import SynthesisSection
    from xerocr.reports.sections.taxonomy import TaxonomySection

    return ReportRenderer(
        (
            SynthesisSection(),
            OverviewSection(),
            EngineSection(),
            DocumentSection(),
            DocumentGallerySection(),
            CrossEngineSection(),
            EconomicsSection(),
            DiagnosticsSection(),
            TaxonomySection(),
            CalibrationSection(),
            GlossarySection(),
        )
    )


__all__ = ["ReportRenderer", "default_report_renderer"]
