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


#: Onglets du rapport (IA en 4 vues — cf. DECISION_RAPPORT_INTERACTIF.md).
_TAB_ORDER = ("overview", "engines", "documents", "crosses")
_TAB_LABELS = {
    "fr": {
        "overview": "Vue d'ensemble",
        "engines": "Par moteur",
        "documents": "Par document",
        "crosses": "Croisements",
    },
    "en": {
        "overview": "Overview",
        "engines": "Engines",
        "documents": "Documents",
        "crosses": "Crosses",
    },
}
_TABLIST_LABEL = {"fr": "Onglets du rapport", "en": "Report tabs"}
#: Section → onglet. Une section absente de la table (ex. ``glossary``) est rendue
#: **après** les panneaux, hors onglets (matière de référence, toujours visible).
_SECTION_TAB = {
    "synthesis": "overview",
    "overview": "overview",
    "by_engine": "engines",
    "calibration": "engines",
    "economics": "engines",
    "taxonomy": "engines",
    "by_document": "documents",
    "documents_gallery": "documents",
    "diagnostics": "documents",
    "cross_engine": "crosses",
}


def _block(name: str, html: str) -> str:
    """Une section = une **région** ancrée (deeplink ``#r-<name>`` + ARIA)."""
    return (
        f'<section id="r-{escape(name)}" class="r-block" '
        f'aria-label="{escape(_label(name))}">{html}</section>'
    )


def _tab_layout(rendered: list[tuple[str, str]], lang: str) -> str:
    """Regroupe les sections en **4 onglets** (enrichissement progressif).

    Sans JS, tous les panneaux restent empilés et visibles (= le rapport plat) ;
    ``report.js`` n'affiche qu'un panneau à la fois. Les onglets sont des **ancres**
    (``href="#panel-<t>"``) → navigation native même sans JS. Sous 2 onglets
    actifs, pas de barre : on empile (une barre d'un onglet est inutile)."""
    by_tab: dict[str, list[str]] = {t: [] for t in _TAB_ORDER}
    trailer: list[str] = []
    for name, html in rendered:
        tab = _SECTION_TAB.get(name)
        bucket = trailer if tab is None else by_tab[tab]
        bucket.append(_block(name, html))
    active = [t for t in _TAB_ORDER if by_tab[t]]
    if len(active) < 2:
        body = "".join("".join(by_tab[t]) for t in active) + "".join(trailer)
        return body
    labels = _TAB_LABELS.get(lang, _TAB_LABELS["fr"])
    tabs = "".join(
        f'<a id="tab-{t}" class="report-tab{" on" if i == 0 else ""}" role="tab" '
        f'href="#panel-{t}" aria-controls="panel-{t}" '
        f'aria-selected="{"true" if i == 0 else "false"}">{escape(labels[t])}</a>'
        for i, t in enumerate(active)
    )
    nav = (
        f'<nav class="report-tabs" role="tablist" '
        f'aria-label="{escape(_TABLIST_LABEL.get(lang, _TABLIST_LABEL["fr"]))}">'
        f"{tabs}</nav>"
    )
    panels = "".join(
        f'<div class="tab-panel" id="panel-{t}" role="tabpanel" '
        f'aria-labelledby="tab-{t}">{"".join(by_tab[t])}</div>'
        for t in active
    )
    return nav + panels + "".join(trailer)


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
        # IA en 4 onglets (regroupement des sections), enrichissement progressif :
        # sections rendues serveur, panneaux ancrés ; ``report.js`` bascule l'affichage.
        body = _tab_layout(rendered, lang)
        # Pied : widget « comparer un run » + script d'interactivité (onglets +
        # navigation clavier + palette). Tous client-side, déterministes, inlinés.
        footer = Html(compare_widget(result) + inline_script("report.js"))
        return render_document(title, Html(body), footer=footer, lang=lang)


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
