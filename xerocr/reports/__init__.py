"""Couche 7 — ``reports`` : sections typées + assemblage HTML autonome.

Lit le ``RunResult`` **directement** (pas de data-layer). ``__init__`` mince.
"""

from __future__ import annotations

from xerocr.reports.compare import MetricDelta, compare_runs, render_comparison
from xerocr.reports.html import escape, render_document
from xerocr.reports.renderer import ReportRenderer, default_report_renderer
from xerocr.reports.section import Html, Section, SectionContext

__all__ = [
    "Html",
    "MetricDelta",
    "ReportRenderer",
    "Section",
    "SectionContext",
    "compare_runs",
    "default_report_renderer",
    "escape",
    "render_comparison",
    "render_document",
]
