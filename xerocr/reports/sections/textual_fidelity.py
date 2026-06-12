"""Section fidélité textuelle : tokens rares + modernisation lexicale (couche 7).

Rend le payload ``textual_fidelity`` en **lecture seule** : par pipeline, le
rappel des tokens rares (avec un échantillon de manqués) et la table de
modernisation lexicale (formes historiques réécrites + variantes produites).
Pédagogie en prose — aucun scalaire de classement (≠ glossaire).
"""

from __future__ import annotations

from xerocr.evaluation.analysis import (
    PipelineTextualFidelity,
    TextualFidelityPayload,
)
from xerocr.evaluation.result import RunResult
from xerocr.reports.html import escape
from xerocr.reports.section import Html, SectionContext


def _rare_row(row: PipelineTextualFidelity) -> str:
    if row.n_rare_reference == 0:
        recall = "—"
        missed = "—"
    else:
        recall = f"{row.rare_recall:.1%}" if row.rare_recall is not None else "—"
        missed = (
            f'<span class="muted">{escape(", ".join(row.missed))}</span>'
            if row.missed
            else "—"
        )
    return (
        f'<tr><td class="eng-cell">{escape(row.pipeline)}</td>'
        f'<td class="disp">{row.n_rare_recalled}/{row.n_rare_reference}</td>'
        f'<td class="disp">{recall}</td>'
        f"<td>{missed}</td></tr>"
    )


def _modernization_rows(row: PipelineTextualFidelity) -> str:
    rows: list[str] = []
    for token in row.modernization:
        variants = ", ".join(
            f"{escape(variant.form)} ×{variant.count}" for variant in token.variants
        )
        rows.append(
            f'<tr><td class="eng-cell">{escape(row.pipeline)}</td>'
            f'<td class="eng-cell">{escape(token.token)}</td>'
            f'<td class="disp">{token.n_modernized}/{token.n_total}</td>'
            f'<td class="disp">{token.rate:.1%}</td>'
            f'<td><span class="muted">{variants}</span></td></tr>'
        )
    return "".join(rows)


def _block(view: str, payload: TextualFidelityPayload) -> str:
    rare_rows = "".join(_rare_row(row) for row in payload.pipelines)
    mod_rows = "".join(_modernization_rows(row) for row in payload.pipelines)
    rare_table = (
        f"<h3>{escape(view)} — rappel des tokens rares "
        f"(≤ {payload.max_freq} occurrence(s))</h3>\n"
        '<p class="muted">Les tokens rares (noms propres, toponymes, termes — '
        "hapax et dis legomena du corpus) pèsent en indexation prosopographique "
        "mais sont noyés dans le CER global. Rappel = part des occurrences rares "
        "de la GT retrouvées (multiset).</p>\n"
        '<table class="data">\n<thead><tr><th>Pipeline</th>'
        '<th class="num-cell">rappelés/total</th><th class="num-cell">rappel</th>'
        "<th>manqués (échantillon)</th></tr></thead>\n"
        f"<tbody>{rare_rows}</tbody>\n</table>\n"
    )
    if not mod_rows:
        return rare_table
    return (
        rare_table
        + f"<h3>{escape(view)} — modernisation lexicale</h3>\n"
        '<p class="muted">Formes historiques de la GT réécrites par le moteur '
        "(diagnostic de prompt LLM) : taux de réécriture et variantes produites "
        "(« ∅ » = mot supprimé).</p>\n"
        '<table class="data">\n<thead><tr><th>Pipeline</th><th>forme GT</th>'
        '<th class="num-cell">réécrits/total</th><th class="num-cell">taux</th>'
        "<th>variantes</th></tr></thead>\n"
        f"<tbody>{mod_rows}</tbody>\n</table>\n"
    )


class TextualFidelitySection:
    """Tokens rares + modernisation lexicale, par pipeline (lecture seule)."""

    name = "textual_fidelity"
    requires: tuple[str, ...] = ()

    def render(self, result: RunResult, ctx: SectionContext) -> Html | None:
        blocks = [
            _block(analysis.view, analysis.payload)
            for analysis in result.analyses
            if isinstance(analysis.payload, TextualFidelityPayload)
        ]
        if not blocks:
            return None
        return Html("<h2>Fidélité textuelle</h2>\n" + "".join(blocks))


__all__ = ["TextualFidelitySection"]
