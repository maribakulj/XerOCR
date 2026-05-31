"""Couche 7 — ``reports`` : sections typées + assemblage HTML autonome.

Lit le ``RunResult`` **directement** (pas de data-layer). ``__init__`` mince.
"""

from __future__ import annotations

from xerocr.reports.html import escape, render_document
from xerocr.reports.renderer import ReportRenderer, default_report_renderer
from xerocr.reports.section import Html, Section, SectionContext

__all__ = [
    "Html",
    "ReportRenderer",
    "Section",
    "SectionContext",
    "default_report_renderer",
    "escape",
    "render_document",
]
