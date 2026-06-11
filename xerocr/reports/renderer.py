"""``ReportRenderer`` — compose des sections en un document HTML autonome.

**Injecté par l'``app``** (reports ne connaît pas app) : ``app`` choisit les
sections. ``default_report_renderer`` fournit le socle (overview) du squelette.
"""

from __future__ import annotations

import base64

from xerocr.evaluation.result import RunResult
from xerocr.reports.compare_widget import compare_widget
from xerocr.reports.csv_export import run_result_csv
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
#: Héros par vue : ``(titre, description)`` localisés (eyebrow + stats dérivés).
_HERO_TEXT = {
    "fr": {
        "overview": (
            "Vue d'ensemble du run",
            "Métadonnées du benchmark, composition du corpus et moteurs exécutés.",
        ),
        "engines": (
            "Par moteur",
            "Comparaison des moteurs sur l'ensemble des métriques calculées.",
        ),
        "documents": (
            "Par document",
            "Chaque document du corpus, avec son CER par moteur.",
        ),
        "crosses": (
            "Croisements",
            "Significativité statistique des écarts entre moteurs.",
        ),
    },
    "en": {
        "overview": (
            "Run overview",
            "Benchmark metadata, corpus composition and engines run.",
        ),
        "engines": ("By engine", "Engine comparison across all computed metrics."),
        "documents": ("By document", "Each corpus document, with its per-engine CER."),
        "crosses": ("Crosses", "Statistical significance of engine differences."),
    },
}
_HERO_EYEBROW = {"fr": "VUE", "en": "VIEW"}
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
    """Une section = sa **propre carte** ``.sec``, région ancrée (``#r-<name>``)."""
    return (
        f'<section id="r-{escape(name)}" class="r-block sec" '
        f'aria-label="{escape(_label(name))}">{html}</section>'
    )


def _hero_stats(tab: str, result: RunResult, lang: str) -> list[tuple[int, str]]:
    """Readouts de portée du **héros**, dérivés du ``RunResult`` (réels, pas figés)."""
    n_docs = result.manifest.n_documents
    n_eng = len({p.pipeline for p in result.pipelines})
    n_met = len({s.metric for p in result.pipelines for s in p.aggregate})
    en = lang == "en"
    docs, eng = "documents", ("engines" if en else "moteurs")
    met = "metrics" if en else "métriques"
    if tab == "overview":
        return [(n_docs, docs), (n_eng, eng)]
    if tab == "engines":
        return [(n_eng, eng), (n_met, met), (n_docs, docs)]
    if tab == "documents":
        return [(n_docs, docs)]
    if tab == "crosses":
        return [(n_eng, eng)]
    return []


def _hero(tab: str, num: int, result: RunResult, lang: str) -> str:
    """Bande **héros** d'un onglet : eyebrow « VUE 0n · NOM » + titre + desc + stats."""
    labels = _TAB_LABELS.get(lang, _TAB_LABELS["fr"])
    title, desc = _HERO_TEXT.get(lang, _HERO_TEXT["fr"])[tab]
    eyebrow = f"{_HERO_EYEBROW.get(lang, 'VUE')} {num:02d} · {labels[tab]}"
    stats = "".join(
        f'<div class="hero-stat"><div class="v">{v}</div>'
        f'<div class="k">{escape(k)}</div></div>'
        for v, k in _hero_stats(tab, result, lang)
    )
    stats_html = f'<div class="view-hero-stats">{stats}</div>' if stats else ""
    return (
        '<div class="view-hero"><div>'
        f'<div class="view-hero-eyebrow">{escape(eyebrow)}</div>'
        f'<div class="view-hero-name">{escape(title)}</div>'
        f'<div class="view-hero-desc">{escape(desc)}</div>'
        f"</div>{stats_html}</div>"
    )


def _tab_layout(
    rendered: list[tuple[str, str]],
    lang: str,
    *,
    result: RunResult | None = None,
) -> tuple[str, str]:
    """Regroupe les sections en **4 onglets** → ``(barre_onglets, corps_panneaux)``.

    La **barre** part dans le chrome ; le **corps** (panneaux) dans ``<main>``.
    Chaque panneau s'ouvre sur un **héros de vue** (si ``result`` fourni). Sans JS,
    tous les panneaux restent empilés et visibles (= le rapport plat) ;
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
        return "", body
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
        f'aria-labelledby="tab-{t}">'
        f"{_hero(t, i + 1, result, lang) if result is not None else ''}"
        f'{"".join(by_tab[t])}</div>'
        for i, t in enumerate(active)
    )
    return nav, panels + "".join(trailer)


def _data_href(text: str, mime: str) -> str:
    """``data:`` URI base64 d'un export — téléchargeable, hors-ligne, déterministe."""
    payload = base64.b64encode(text.encode("utf-8")).decode("ascii")
    return f"data:{mime};charset=utf-8;base64,{payload}"


def _chrome_meta(result: RunResult, lang: str) -> str:
    """Méta de run (docs/moteurs/date) + boutons d'export **CSV/JSON**.

    Exports = ``<a download>`` vers des ``data:`` URI (zéro JS, autonome,
    hors-ligne). Le JSON embarqué est le ``RunResult`` complet — la matière à
    redonner à un outil tiers (cf. saveur « données » du cadre rapport)."""
    n_docs = result.manifest.n_documents
    n_engines = len({p.pipeline for p in result.pipelines})
    date = result.manifest.completed_at.date().isoformat()
    docs_lbl = "docs"
    eng_lbl = "engines" if lang == "en" else "moteurs"
    csv_href = _data_href(run_result_csv(result), "text/csv")
    json_href = _data_href(result.model_dump_json(), "application/json")
    stem = escape(result.manifest.run_id)
    return (
        '<div class="chrome-meta">'
        f'<span><span class="v">{n_docs}</span> {docs_lbl}</span>'
        f'<span><span class="v">{n_engines}</span> {eng_lbl}</span>'
        f'<span class="v">{escape(date)}</span>'
        '<div class="chrome-actions">'
        f'<a class="chrome-btn" download="{stem}.csv" href="{csv_href}">⬇ CSV</a>'
        f'<a class="chrome-btn" download="{stem}.json" href="{json_href}">⬇ JSON</a>'
        "</div></div>"
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
        # IA en 4 onglets : barre (→ chrome) + panneaux (→ corps). Enrichissement
        # progressif : sections rendues serveur ; ``report.js`` bascule l'affichage.
        tabs, body = _tab_layout(rendered, lang, result=result)
        meta = _chrome_meta(result, lang)
        # Pied : widget « comparer un run » + script d'interactivité (onglets +
        # navigation clavier + palette). Tous client-side, déterministes, inlinés.
        footer = Html(compare_widget(result) + inline_script("report.js"))
        return render_document(
            title, Html(body), footer=footer, lang=lang, tabs=tabs, meta=meta
        )


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
