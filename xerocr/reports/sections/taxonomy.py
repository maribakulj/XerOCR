"""Section taxonomie : répartition des classes d'erreurs (couche 7).

Rend les payloads ``taxonomy`` en **lecture seule** : pour chaque pipeline,
les classes d'erreurs et leur part — quelles erreurs, pas seulement combien.
"""

from __future__ import annotations

from xerocr.evaluation.analysis import TaxonomyPayload
from xerocr.evaluation.result import RunResult
from xerocr.reports.html import escape
from xerocr.reports.section import Html, SectionContext


def _block(view: str, payload: TaxonomyPayload) -> str:
    rows: list[str] = []
    for pipeline in payload.pipelines:
        for item in pipeline.counts:
            share = item.count / pipeline.total_errors
            rows.append(
                f'<tr><td class="eng-cell">{escape(pipeline.pipeline)}</td>'
                f'<td class="eng-cell">{escape(item.label)}</td>'
                f'<td class="disp">{item.count}</td>'
                f'<td class="disp">{share:.1%}</td></tr>'
            )
    return (
        f"<h3>{escape(view)} — classes d'erreurs</h3>\n"
        '<p class="muted">Classification par règles pures (casse, diacritiques, '
        "ligatures, confusions visuelles, segmentation, lacunes, insertions) — "
        "part relative au total des erreurs de mots du pipeline.</p>\n"
        '<table class="data">\n<thead><tr><th>Pipeline</th><th>classe</th>'
        '<th class="num-cell">occurrences</th><th class="num-cell">part</th>'
        "</tr></thead>\n"
        f"<tbody>{''.join(rows)}</tbody>\n</table>\n"
    )


class TaxonomySection:
    """Répartition des classes d'erreurs par pipeline."""

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


__all__ = ["TaxonomySection"]
