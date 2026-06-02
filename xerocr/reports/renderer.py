"""``ReportRenderer`` — compose des sections en un document HTML autonome.

**Injecté par l'``app``** (reports ne connaît pas app) : ``app`` choisit les
sections. ``default_report_renderer`` fournit le socle (overview) du squelette.
"""

from __future__ import annotations

from xerocr.evaluation.result import RunResult
from xerocr.reports.html import render_document
from xerocr.reports.section import Html, Section, SectionContext


class ReportRenderer:
    """Assemble les sections applicables en un rapport HTML."""

    def __init__(self, sections: tuple[Section, ...]) -> None:
        self._sections = sections

    def render(self, result: RunResult, *, title: str = "XerOCR — rapport") -> str:
        known = {
            score.metric
            for pipeline in result.pipelines
            for score in pipeline.aggregate
        }
        ctx = SectionContext(title=title)
        fragments: list[str] = []
        for section in self._sections:
            if section.requires and not set(section.requires) <= known:
                continue  # no-orphan : métriques requises absentes
            html = section.render(result, ctx)
            if html is not None:
                fragments.append(html)
        return render_document(title, Html("".join(fragments)))


def default_report_renderer() -> ReportRenderer:
    """Renderer du socle : overview + par-document + significativité inter-moteurs."""
    from xerocr.reports.sections.by_document import DocumentSection
    from xerocr.reports.sections.cross_engine import CrossEngineSection
    from xerocr.reports.sections.overview import OverviewSection

    return ReportRenderer(
        (OverviewSection(), DocumentSection(), CrossEngineSection())
    )


__all__ = ["ReportRenderer", "default_report_renderer"]
