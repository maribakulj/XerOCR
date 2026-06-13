"""Section taxonomie : composition des classes d'erreurs (couche 7).

Rend les payloads ``taxonomy`` en **lecture seule** : par pipeline, une **barre
empilée SVG** (part de chaque classe) + une légende (classe · part · occurrences)
— quelles erreurs, pas seulement combien. Sous 2 moteurs ou plus, un **profil
comparatif** (classe × moteur, part en databar) donne l'autre lecture : non plus
la composition d'un moteur, mais quel moteur est lourd sur *quelle* classe (#5).
Server-side, déterministe, zéro JS.
"""

from __future__ import annotations

from collections.abc import Mapping

from xerocr.evaluation.analysis import PipelineTaxonomy, TaxonomyPayload
from xerocr.evaluation.result import RunResult
from xerocr.reports.engine_badges import engine_accent, engine_cell, engine_order
from xerocr.reports.html import escape
from xerocr.reports.section import Html, SectionContext
from xerocr.reports.svg import composition_bar

#: Libellés bilingues du **profil comparatif** (le reste de la section, antérieur
#: à la consigne FR/EN des graphiques, reste FR — i18n du rapport = jalon à part).
_PROFILE_TEXT: dict[str, dict[str, str]] = {
    "fr": {
        "title": "profil comparatif des moteurs",
        "intro": (
            "Part de chaque classe d'erreur, moteur par moteur — lire une "
            "<strong>ligne</strong> pour comparer les moteurs sur une classe (qui "
            "est lourd en diacritiques, en segmentation…). « · » = classe absente "
            "chez ce moteur."
        ),
        "th_class": "Classe d'erreur",
    },
    "en": {
        "title": "comparative engine profile",
        "intro": (
            "Share of each error class, engine by engine — read a <strong>row</strong> "
            "to compare engines on one class (which is heavy on diacritics, "
            "segmentation…). “·” = class absent for that engine."
        ),
        "th_class": "Error class",
    },
}


def composition_html(classes: tuple[str, ...], pipeline: PipelineTaxonomy) -> str:
    """Barre empilée + légende pour **un** pipeline (réutilisable : section + profil).

    Couleur par classe = palette cyclique partagée, indexée sur l'ordre canonique
    ``classes``. Renvoie ``""`` si le pipeline n'a aucune erreur classée."""
    color = {cls: engine_accent(i) for i, cls in enumerate(classes)}

    def _c(label: str) -> str:
        return color.get(label, engine_accent(0))

    total = pipeline.total_errors
    present = [(c.label, c.count) for c in pipeline.counts if c.count > 0]
    if not present:
        return ""
    segments = [(cnt / total, _c(lbl)) for lbl, cnt in present]
    legend = "".join(
        f'<div class="comp-row">'
        f'<span class="comp-sw" style="background:{_c(lbl)}"></span>'
        f'<span class="comp-label">{escape(lbl)}</span>'
        f'<span class="comp-share mono">{cnt / total:.0%}</span>'
        f'<span class="comp-count mono">{cnt}</span></div>'
        for lbl, cnt in present
    )
    return (
        f'<div class="comp">{composition_bar(segments)}'
        f'<div class="comp-legend">{legend}</div></div>'
    )


def _profile_block(
    view: str, payload: TaxonomyPayload, order: Mapping[str, int], lang: str
) -> str:
    """Profil comparatif (#5) : classe × moteur, part en databar (lecture par ligne).

    Complémentaire des barres empilées par-moteur ci-dessus (lecture par moteur) :
    ici on lit une **classe** à travers les moteurs. **À 2 moteurs et plus** (à 1,
    la barre suffit — pas de comparaison). Pure présentation du payload."""
    if len(payload.pipelines) < 2:
        return ""
    present = [
        cls
        for cls in payload.classes
        if any(
            count.label == cls and count.count > 0
            for pipeline in payload.pipelines
            for count in pipeline.counts
        )
    ]
    if not present:
        return ""
    text = _PROFILE_TEXT.get(lang, _PROFILE_TEXT["fr"])
    headers = "".join(
        f'<th class="num-cell">{engine_cell(p.pipeline, order.get(p.pipeline, 0))}</th>'
        for p in payload.pipelines
    )
    rows: list[str] = []
    for cls in present:
        cells: list[str] = []
        for pipeline in payload.pipelines:
            count = next((c.count for c in pipeline.counts if c.label == cls), 0)
            share = count / pipeline.total_errors if pipeline.total_errors else 0.0
            if count > 0:
                cells.append(
                    '<td class="databar">'
                    f'<span class="db-fill" style="width:{round(share * 100)}%">'
                    f'</span><span class="db-num">{share:.0%}</span></td>'
                )
            else:
                cells.append('<td class="databar"><span class="db-num">·</span></td>')
        rows.append(f'<tr><td class="eng-cell">{escape(cls)}</td>{"".join(cells)}</tr>')
    return (
        f"<h3>{escape(view)} — {text['title']}</h3>\n"
        f'<p class="muted">{text["intro"]}</p>\n'
        '<table class="data">\n'
        f'<thead><tr><th>{text["th_class"]}</th>{headers}</tr></thead>\n'
        f"<tbody>{''.join(rows)}</tbody>\n</table>\n"
    )


def _block(
    view: str, payload: TaxonomyPayload, order: Mapping[str, int], lang: str
) -> str:
    parts: list[str] = [
        f"<h3>{escape(view)} — composition des erreurs</h3>\n",
        '<p class="muted">Classification par règles pures (casse, diacritiques, '
        "ligatures, confusions visuelles, segmentation, lacunes, insertions) — "
        "part relative au total des erreurs de mots du pipeline.</p>\n",
    ]
    for pipeline in payload.pipelines:
        block = composition_html(payload.classes, pipeline)
        if block:
            parts.append(
                f"<h4>{escape(pipeline.pipeline)} — "
                f"{pipeline.total_errors} erreurs</h4>\n{block}\n"
            )
    parts.append(_profile_block(view, payload, order, lang))
    return "".join(parts)


class TaxonomySection:
    """Composition des classes d'erreurs par pipeline (barre empilée + légende)."""

    name = "taxonomy"
    requires: tuple[str, ...] = ()

    def render(self, result: RunResult, ctx: SectionContext) -> Html | None:
        order = engine_order(p.pipeline for p in result.pipelines)
        blocks = [
            _block(analysis.view, analysis.payload, order, ctx.lang)
            for analysis in result.analyses
            if isinstance(analysis.payload, TaxonomyPayload)
        ]
        if not blocks:
            return None
        return Html("<h2>Taxonomie des erreurs</h2>\n" + "".join(blocks))


__all__ = ["TaxonomySection", "composition_html"]
