"""Section taxonomie : composition des classes d'erreurs (couche 7).

Rend les payloads ``taxonomy`` en **lecture seule** : par pipeline, une **barre
empilée SVG** (part de chaque classe) + une légende (classe · part · occurrences)
— quelles erreurs, pas seulement combien. Server-side, déterministe, zéro JS.
"""

from __future__ import annotations

from xerocr.evaluation.analysis import PipelineTaxonomy, TaxonomyPayload
from xerocr.evaluation.result import RunResult
from xerocr.reports.engine_badges import engine_accent
from xerocr.reports.html import escape
from xerocr.reports.section import Html, SectionContext
from xerocr.reports.svg import composition_bar


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


def _block(view: str, payload: TaxonomyPayload) -> str:
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
    return "".join(parts)


class TaxonomySection:
    """Composition des classes d'erreurs par pipeline (barre empilée + légende)."""

    name = "taxonomy"
    requires: tuple[str, ...] = ()

    def render(self, result: RunResult, ctx: SectionContext) -> Html | None:
        blocks = [
            _block(analysis.view, analysis.payload)
            for analysis in result.analyses
            if isinstance(analysis.payload, TaxonomyPayload)
        ]
        if not blocks:
            return None
        return Html("<h2>Taxonomie des erreurs</h2>\n" + "".join(blocks))


__all__ = ["TaxonomySection", "composition_html"]
