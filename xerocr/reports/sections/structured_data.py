"""Section données structurées : la survie des dates/folios/montants (couche 7).

Rend le payload ``structured_data`` en **lecture seule** : par pipeline et par
catégorie présente dans la GT, restitution stricte (forme exacte) et en valeur
(équivalent), avec les formes perdues à l'appui.
"""

from __future__ import annotations

from xerocr.evaluation.analysis import StructuredDataPayload
from xerocr.evaluation.result import RunResult
from xerocr.reports.html import escape, localized
from xerocr.reports.section import Html, SectionContext

_CATEGORY_LABELS = {
    "year": ("années", "years"),
    "foliation": ("foliotation", "foliation"),
    "currency": ("montants", "amounts"),
    "regnal": ("années régnales", "regnal years"),
}


def _category_label(category: str, lang: str) -> str:
    pair = _CATEGORY_LABELS.get(category)
    if pair is None:
        return category
    return localized(lang, pair[0], pair[1])


def _block(view: str, payload: StructuredDataPayload, lang: str) -> str:
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
                f"{escape(_category_label(item.category, lang))}</td>"
                f'<td class="disp">{item.n_total}</td>'
                f'<td class="disp">{item.strict_score:.1%}</td>'
                f'<td class="disp">{item.value_score:.1%}</td>'
                f'<td class="disp">{lost}</td></tr>'
            )
    head = localized(
        lang,
        f"{escape(view)} — séquences numériques",
        f"{escape(view)} — numeric sequences",
    )
    prose = localized(
        lang,
        '<p class="muted">Ce que cite un historien : années, folios '
        "(recto/verso distingués), montants, années régnales. « strict » = la "
        "forme exacte de la GT survit ; « valeur » = l'équivalent survit "
        "(« f. 12r » vaut « fol. 12r », « an 3 » vaut « an III »). Détection "
        "par motifs conservateurs — la précision prime sur le rappel.</p>\n",
        '<p class="muted">What a historian cites: years, folios '
        "(recto/verso distinguished), amounts, regnal years. \"strict\" = the "
        "exact GT form is preserved; \"value\" = the equivalent is preserved "
        '("f. 12r" matches "fol. 12r", "an 3" matches "an III"). Detection '
        "by conservative patterns — precision takes priority over recall.</p>\n",
    )
    th_pipeline = localized(lang, "Pipeline", "Pipeline")
    th_category = localized(lang, "catégorie", "category")
    th_strict = localized(lang, "strict", "strict")
    th_value = localized(lang, "valeur", "value")
    th_lost = localized(lang, "perdues", "lost")
    return (
        f"<h3>{head}</h3>\n"
        f"{prose}"
        f'<table class="data">\n<thead><tr><th>{th_pipeline}</th>'
        f"<th>{th_category}</th>"
        f'<th class="num-cell">n</th><th class="num-cell">{th_strict}</th>'
        f'<th class="num-cell">{th_value}</th><th>{th_lost}</th></tr></thead>\n'
        f"<tbody>{''.join(rows)}</tbody>\n</table>\n"
    )


class StructuredDataSection:
    """Restitution des séquences numériques, par pipeline et catégorie."""

    name = "structured_data"
    requires: tuple[str, ...] = ()

    def render(self, result: RunResult, ctx: SectionContext) -> Html | None:
        blocks = [
            _block(analysis.view, analysis.payload, ctx.lang)
            for analysis in result.analyses
            if isinstance(analysis.payload, StructuredDataPayload)
        ]
        if not blocks:
            return None
        title = localized(ctx.lang, "Données structurées", "Structured data")
        return Html(f"<h2>{title}</h2>\n" + "".join(blocks))


__all__ = ["StructuredDataSection"]
