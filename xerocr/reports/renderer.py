"""``ReportRenderer`` — compose des sections en un document HTML autonome.

**Injecté par l'``app``** (reports ne connaît pas app) : ``app`` choisit les
sections. ``default_report_renderer`` fournit le socle (overview) du squelette.
"""

from __future__ import annotations

import base64
from collections.abc import Mapping

from xerocr.evaluation.result import RunResult
from xerocr.reports.compare_widget import compare_widget
from xerocr.reports.csv_export import run_result_csv
from xerocr.reports.embedded import inline_script
from xerocr.reports.glossary_panel import glossary_chrome_link, glossary_dialog
from xerocr.reports.html import escape, render_document
from xerocr.reports.section import Html, Section, SectionContext

#: Libellés FR des sections pour le sommaire (deeplinks) ; repli = nom brut.
_SECTION_LABELS = {
    "synthesis": "Synthèse",
    "overview": "Vue d'ensemble",
    "corpus_composition": "Composition",
    "by_engine": "Par moteur",
    "engine_radar": "Profil radar",
    "metric_columns": "Colonnes métriques",
    "rank_bump": "Bascule de classement",
    "engine_profiles": "Profils moteur",
    "document_details": "Détail document",
    "documents": "Par document",
    "image_quality": "Qualité image",
    "quality_error": "Qualité × erreur",
    "dispersion": "Dispersion",
    "cross_engine": "Inter-moteurs",
    "engine_duel": "Duel par document",
    "word_errors": "Carte des mots",
    "conformity": "Conformité HIPE",
    "structure": "Structure",
    "correction": "Bilan de correction",
    "structured_data": "Données structurées",
    "philology": "Philologie",
    "textual_fidelity": "Fidélité textuelle",
    "lines": "Par ligne",
    "ner": "Entités nommées",
    "economics": "Économie",
    "diagnostics": "Diagnostic",
    "taxonomy": "Taxonomie",
    "calibration": "Calibration",
    "methodology": "Méthodologie",
}

#: Libellés **EN** des sections (parité de clés avec ``_SECTION_LABELS``) — pour
#: l'``aria-label`` des blocs quand le rapport est rendu en anglais (``?lang=en``).
_SECTION_LABELS_EN = {
    "synthesis": "Synthesis",
    "overview": "Overview",
    "corpus_composition": "Composition",
    "by_engine": "By engine",
    "engine_radar": "Radar profile",
    "metric_columns": "Metric columns",
    "rank_bump": "Ranking shift",
    "engine_profiles": "Engine profiles",
    "document_details": "Document detail",
    "documents": "By document",
    "image_quality": "Image quality",
    "quality_error": "Quality × error",
    "dispersion": "Dispersion",
    "cross_engine": "Cross-engine",
    "engine_duel": "Per-document duel",
    "conformity": "HIPE conformity",
    "structure": "Layout structure",
    "correction": "Correction balance",
    "structured_data": "Structured data",
    "philology": "Philology",
    "textual_fidelity": "Textual fidelity",
    "lines": "Per line",
    "ner": "Named entities",
    "economics": "Economics",
    "diagnostics": "Diagnostics",
    "taxonomy": "Taxonomy",
    "calibration": "Calibration",
    "methodology": "Methodology",
}


def _label(name: str, lang: str = "fr") -> str:
    table = _SECTION_LABELS_EN if lang == "en" else _SECTION_LABELS
    return table.get(name, name)


#: Onglets du rapport (IA par **unité d'analyse** : corpus → moteur → document).
#: « Croisements » a été fondu dans « Par moteur » : comparer tous les moteurs
#: (classement, radar, significativité, recouvrement) EST une analyse moteur ;
#: un onglet séparé dédoublait la taxonomie (cf. DECISION_RAPPORT_INTERACTIF.md).
_TAB_ORDER = ("overview", "engines", "documents")
_TAB_LABELS = {
    "fr": {
        "overview": "Vue d'ensemble",
        "engines": "Par moteur",
        "documents": "Par document",
    },
    "en": {
        "overview": "Overview",
        "engines": "Engines",
        "documents": "Documents",
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
    },
    "en": {
        "overview": (
            "Run overview",
            "Benchmark metadata, corpus composition and engines run.",
        ),
        "engines": ("By engine", "Engine comparison across all computed metrics."),
        "documents": ("By document", "Each corpus document, with its per-engine CER."),
    },
}
_HERO_EYEBROW = {"fr": "VUE", "en": "VIEW"}
#: Section → onglet. Une section absente de la table (ex. ``glossary``) est rendue
#: **après** les panneaux, hors onglets (matière de référence, toujours visible).
_SECTION_TAB = {
    "synthesis": "overview",
    "overview": "overview",
    "corpus_composition": "overview",
    "by_engine": "engines",
    "engine_radar": "engines",
    "metric_columns": "engines",
    "rank_bump": "engines",
    "engine_profiles": "engines",
    "dispersion": "engines",
    "calibration": "engines",
    "conformity": "engines",
    "structure": "engines",
    "correction": "engines",
    "structured_data": "engines",
    "philology": "engines",
    "textual_fidelity": "engines",
    "lines": "engines",
    "ner": "engines",
    "economics": "engines",
    "taxonomy": "engines",
    "documents": "documents",
    "document_details": "documents",
    "diagnostics": "documents",
    "image_quality": "documents",
    "quality_error": "documents",
    # « Croisements » fondu dans « Par moteur » : comparer les moteurs entre eux
    # (significativité, recouvrement) appartient à l'analyse moteur.
    "cross_engine": "engines",
    "engine_duel": "engines",
    "word_errors": "engines",
}

#: Section « **détail** » de chaque onglet maître/détail : elle n'est PAS rendue
#: dans le flux maître (liste/comparaison) mais dans un conteneur ``.tab-detail``
#: séparé que ``report.js`` **échange** avec le maître au clic (vraie navigation
#: liste → page, ≠ ancre dans le même défilement). Les autres onglets n'ont pas
#: de détail.
_DETAIL_SECTION: dict[str, str] = {
    "engines": "engine_profiles",
    "documents": "document_details",
}


#: Regroupement thématique des sections de l'onglet **« engines »** (riche : ~17
#: sections). ``(clé, libellé_fr, libellé_en, sections…)`` — un sous-titre pleine
#: largeur est inséré avant chaque groupe **présent** (cf. ``_panel_body``). Toute
#: section ``engines`` doit figurer dans un groupe (garde-fou
#: ``test_engine_groups_cover_engines_tab``) ; sinon elle est rendue à la fin, sans
#: sous-titre. Pur regroupement visuel (aucun JS, imprimable).
_ENGINE_GROUPS: tuple[tuple[str, str, str, tuple[str, ...]], ...] = (
    (
        "compare",
        "Comparaison des moteurs",
        "Engine comparison",
        ("by_engine", "engine_radar", "metric_columns", "rank_bump",
         "dispersion"),
    ),
    (
        "crosses",
        "Significativité & recouvrement",
        "Significance & overlap",
        ("cross_engine", "engine_duel", "word_errors"),
    ),
    (
        "errors",
        "Familles d'erreurs & analyses fines",
        "Error families & fine-grained analyses",
        ("conformity", "structure", "correction", "structured_data", "philology",
         "textual_fidelity", "lines", "ner", "taxonomy", "calibration"),
    ),
    ("economics", "Économie", "Economics", ("economics",)),
)


def _panel_body(tab: str, blocks: list[tuple[str, str]], lang: str) -> str:
    """Corps d'un panneau : les blocs joints, dans l'ordre. Pour l'onglet riche
    « engines », on **regroupe** par thème (``_ENGINE_GROUPS``) et on insère un
    **sous-titre pleine largeur** avant chaque groupe présent (pur balisage, zéro
    JS, imprimable, sans-JS lisible). Une section engines hors groupe (cas
    défensif) est rendue à la fin, sans sous-titre, dans son ordre d'origine."""
    if tab != "engines":
        return "".join(html for _, html in blocks)
    by_name = {name: html for name, html in blocks}
    parts: list[str] = []
    used: set[str] = set()
    for _key, fr, en, names in _ENGINE_GROUPS:
        present = [n for n in names if n in by_name]
        if not present:
            continue
        label = escape(en if lang == "en" else fr)
        parts.append(f'<h2 class="tab-subhead">{label}</h2>')
        for n in present:
            parts.append(by_name[n])
            used.add(n)
    parts.extend(html for name, html in blocks if name not in used)
    return "".join(parts)


#: Sections **intrinsèquement larges** (tableaux multi-colonnes, galeries, charts
#: pleine largeur) : elles prennent toute la largeur dans le flux de cartes
#: (``column-span:all``). Les autres (petits charts/listes) s'écoulent en colonnes.
_WIDE_SECTIONS: frozenset[str] = frozenset({
    "synthesis", "overview", "by_engine", "engine_profiles", "conformity",
    "structured_data", "ner", "lines", "economics", "cross_engine",
    "word_errors", "taxonomy", "correction", "textual_fidelity", "documents",
    "diagnostics", "image_quality",
})


def _block(name: str, html: str, lang: str) -> str:
    """Une section = sa **propre carte** ``.sec``, région ancrée (``#r-<name>``)."""
    wide = " r-wide" if name in _WIDE_SECTIONS else ""
    return (
        f'<section id="r-{escape(name)}" class="r-block sec{wide}" '
        f'aria-label="{escape(_label(name, lang))}">{html}</section>'
    )


def _hero_stats(tab: str, result: RunResult, lang: str) -> list[tuple[int, str]]:
    """Readouts de portée du **héros**, dérivés du ``RunResult`` (réels, pas figés)."""
    n_docs = result.manifest.n_documents
    n_eng = len({p.pipeline for p in result.pipelines})
    n_met = len({s.metric for p in result.pipelines for s in p.aggregate})
    n_strata = len({d.stratum for d in result.documents if d.stratum})
    en = lang == "en"
    docs, eng = "documents", ("engines" if en else "moteurs")
    met = "metrics" if en else "métriques"
    strata_lbl = "strata" if en else "strates"
    if tab == "overview":
        base = [(n_docs, docs), (n_eng, eng)]
        # « N strates » seulement si le corpus en porte (jamais un faux compteur).
        return base + [(n_strata, strata_lbl)] if n_strata else base
    if tab == "engines":
        return [(n_eng, eng), (n_met, met), (n_docs, docs)]
    if tab == "documents":
        return [(n_docs, docs)]
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


def _panel_inner(tab: str, blocks: list[tuple[str, str]], lang: str, hero: str) -> str:
    """Corps d'un onglet en **maître/détail** : la vue **maître** (héros + sections
    de liste/comparaison, wrappées en cartes ``.sec``) et la vue **détail** (la
    section ``_DETAIL_SECTION`` brute — fiches moteur/document) dans deux conteneurs
    ``.tab-master`` / ``.tab-detail`` que ``report.js`` **échange** au clic (vraie
    page, ≠ ancre). Sans JS, les deux restent visibles (les fiches via ``:target``)."""
    detail_name = _DETAIL_SECTION.get(tab)
    master_blocks = [(n, _block(n, h, lang)) for n, h in blocks if n != detail_name]
    detail_raw = next((h for n, h in blocks if n == detail_name), "")
    body = _panel_body(tab, master_blocks, lang)
    master = f'<div class="tab-master">{hero}{body}</div>'
    detail = (
        f'<div class="tab-detail" data-tab="{escape(tab)}">{detail_raw}</div>'
        if detail_raw
        else ""
    )
    return master + detail


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
    by_tab: dict[str, list[tuple[str, str]]] = {t: [] for t in _TAB_ORDER}
    trailer: list[str] = []
    for name, html in rendered:
        tab = _SECTION_TAB.get(name)
        if tab is None:
            trailer.append(_block(name, html, lang))
        else:
            by_tab[tab].append((name, html))  # html brut (maître/détail au montage)
    active = [t for t in _TAB_ORDER if by_tab[t]]
    if len(active) < 2:
        body = "".join(_panel_inner(t, by_tab[t], lang, "") for t in active) + "".join(
            trailer
        )
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
    def _one_panel(i: int, t: str) -> str:
        hero = _hero(t, i + 1, result, lang) if result is not None else ""
        return (
            f'<div class="tab-panel" id="panel-{t}" role="tabpanel" '
            f'aria-labelledby="tab-{t}">{_panel_inner(t, by_tab[t], lang, hero)}</div>'
        )

    panels = "".join(
        _one_panel(i, t)
        for i, t in enumerate(active)
    )
    return nav, panels + "".join(trailer)


def _data_href(text: str, mime: str) -> str:
    """``data:`` URI base64 d'un export — téléchargeable, hors-ligne, déterministe."""
    payload = base64.b64encode(text.encode("utf-8")).decode("ascii")
    return f"data:{mime};charset=utf-8;base64,{payload}"


def _chrome_meta(result: RunResult, lang: str, *, glossary_btn: str = "") -> str:
    """Méta de run (docs/moteurs/date) + actions (**Glossaire** · CSV · JSON).

    Exports = ``<a download>`` vers des ``data:`` URI (zéro JS, autonome,
    hors-ligne). Le JSON embarqué est le ``RunResult`` complet — la matière à
    redonner à un outil tiers (cf. saveur « données » du cadre rapport).
    ``glossary_btn`` (lien-ancre vers le dialog) précède les exports ; vide si
    aucune métrique présente n'a d'entrée de glossaire."""
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
        f"{glossary_btn}"
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
        images: Mapping[str, str] | None = None,
        facsimiles: Mapping[str, str] | None = None,
    ) -> str:
        known = {
            score.metric
            for pipeline in result.pipelines
            for score in pipeline.aggregate
        }
        ctx = SectionContext(
            title=title,
            lang=lang,
            images=images or {},
            facsimiles=facsimiles or {},
        )
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
        # Glossaire = périphérie (chrome) : dialog (vide si aucune métrique connue
        # n'a d'entrée) + lien-ancre dans la barre d'actions.
        gloss_dialog = glossary_dialog(known, lang)
        gloss_link = glossary_chrome_link(lang) if gloss_dialog else ""
        meta = _chrome_meta(result, lang, glossary_btn=gloss_link)
        # Pied : widget « comparer un run » + dialog glossaire + script (onglets +
        # dialog + nav clavier + palette). Tous client-side, déterministes, inlinés.
        footer = Html(
            compare_widget(result) + gloss_dialog + inline_script("report.js")
        )
        return render_document(
            title, Html(body), footer=footer, lang=lang, tabs=tabs, meta=meta
        )


def default_report_renderer() -> ReportRenderer:
    """Socle : synthèse, overview, par-moteur/document, stats, économie,
    diagnostic. Le glossaire est **hors sections** (dialog du chrome)."""
    from xerocr.reports.sections.by_engine import EngineSection
    from xerocr.reports.sections.calibration import CalibrationSection
    from xerocr.reports.sections.conformity import ConformitySection
    from xerocr.reports.sections.corpus_composition import CorpusCompositionSection
    from xerocr.reports.sections.correction import CorrectionSection
    from xerocr.reports.sections.cross_engine import CrossEngineSection
    from xerocr.reports.sections.diagnostics import DiagnosticsSection
    from xerocr.reports.sections.dispersion import DispersionSection
    from xerocr.reports.sections.document_detail import DocumentDetailSection
    from xerocr.reports.sections.documents import DocumentsSection
    from xerocr.reports.sections.economics import EconomicsSection
    from xerocr.reports.sections.engine_duel import EngineDuelSection
    from xerocr.reports.sections.engine_profile import EngineProfileSection
    from xerocr.reports.sections.engine_radar import EngineRadarSection
    from xerocr.reports.sections.image_quality import ImageQualitySection
    from xerocr.reports.sections.lines import LinesSection
    from xerocr.reports.sections.methodology import MethodologySection
    from xerocr.reports.sections.metric_columns import MetricColumnsSection
    from xerocr.reports.sections.ner import NerSection
    from xerocr.reports.sections.overview import OverviewSection
    from xerocr.reports.sections.philology import PhilologySection
    from xerocr.reports.sections.quality_error import QualityErrorSection
    from xerocr.reports.sections.rank_bump import RankBumpSection
    from xerocr.reports.sections.structure import StructureSection
    from xerocr.reports.sections.structured_data import StructuredDataSection
    from xerocr.reports.sections.synthesis import SynthesisSection
    from xerocr.reports.sections.taxonomy import TaxonomySection
    from xerocr.reports.sections.textual_fidelity import TextualFidelitySection
    from xerocr.reports.sections.word_errors import WordErrorsSection

    return ReportRenderer(
        (
            SynthesisSection(),
            OverviewSection(),
            CorpusCompositionSection(),
            EngineSection(),
            EngineRadarSection(),
            MetricColumnsSection(),
            RankBumpSection(),
            EngineProfileSection(),
            DispersionSection(),
            DocumentsSection(),
            DocumentDetailSection(),
            ImageQualitySection(),
            QualityErrorSection(),
            CrossEngineSection(),
            WordErrorsSection(),
            EngineDuelSection(),
            ConformitySection(),
            StructureSection(),
            CorrectionSection(),
            StructuredDataSection(),
            PhilologySection(),
            TextualFidelitySection(),
            LinesSection(),
            NerSection(),
            EconomicsSection(),
            DiagnosticsSection(),
            TaxonomySection(),
            CalibrationSection(),
            MethodologySection(),
        )
    )


__all__ = ["ReportRenderer", "default_report_renderer"]
