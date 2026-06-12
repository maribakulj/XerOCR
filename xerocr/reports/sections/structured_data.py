"""Section données structurées : la survie des dates/folios/montants (couche 7).

Rend le payload ``structured_data`` en **lecture seule** : par pipeline et par
catégorie présente dans la GT, restitution stricte (forme exacte) et en valeur
(équivalent), avec les formes perdues à l'appui.
"""

from __future__ import annotations

from xerocr.evaluation.analysis import StructuredDataPayload
from xerocr.evaluation.result import RunResult
from xerocr.reports.html import escape
from xerocr.reports.section import Html, SectionContext

_CATEGORY_LABELS = {
    "year": "années",
    "foliation": "foliotation",
    "currency": "montants",
    "regnal": "années régnales",
}


def _block(view: str, payload: StructuredDataPayload) -> str:
    rows: list[str] = []
    for pipeline in payload.pipelines:
        for item in pipeline.categories:
            lost = (
                f'<span class="muted">{escape(", ".join(item.lost))}</span>'
                if item.lost
                else "—"
            )
            rows.append(
                f'<tr><td class="eng-cell">{escape(pipeline.pipeline)}</td>'
                f'<td class="eng-cell">'
                f"{escape(_CATEGORY_LABELS.get(item.category, item.category))}</td>"
                f'<td class="disp">{item.n_total}</td>'
                f'<td class="disp">{item.strict_score:.1%}</td>'
                f'<td class="disp">{item.value_score:.1%}</td>'
                f'<td class="disp">{lost}</td></tr>'
            )
    return (
        f"<h3>{escape(view)} — séquences numériques</h3>\n"
        '<p class="muted">Ce que cite un historien : années, folios '
        "(recto/verso distingués), montants, années régnales. « strict » = la "
        "forme exacte de la GT survit ; « valeur » = l'équivalent survit "
        "(« f. 12r » vaut « fol. 12r », « an 3 » vaut « an III »). Détection "
        "par motifs conservateurs — la précision prime sur le rappel.</p>\n"
        '<table class="data">\n<thead><tr><th>Pipeline</th><th>catégorie</th>'
        '<th class="num-cell">n</th><th class="num-cell">strict</th>'
        '<th class="num-cell">valeur</th><th>perdues</th></tr></thead>\n'
        f"<tbody>{''.join(rows)}</tbody>\n</table>\n"
    )


class StructuredDataSection:
    """Restitution des séquences numériques, par pipeline et catégorie."""

    name = "structured_data"
    requires: tuple[str, ...] = ()

    def render(self, result: RunResult, ctx: SectionContext) -> Html | None:
        blocks = [
            _block(analysis.view, analysis.payload)
            for analysis in result.analyses
            if isinstance(analysis.payload, StructuredDataPayload)
        ]
        if not blocks:
            return None
        return Html("<h2>Données structurées</h2>\n" + "".join(blocks))


__all__ = ["StructuredDataSection"]
