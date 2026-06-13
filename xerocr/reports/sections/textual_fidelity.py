"""Section fidélité textuelle : tokens rares + modernisation lexicale (couche 7).

Rend le payload ``textual_fidelity`` en **lecture seule** : par pipeline, le
rappel des tokens rares (avec un échantillon de manqués) et le **flux de
modernisation** (#17) — forme historique de la GT → variantes produites, chips
dimensionnés par fréquence (« voir les tokens réécrits »). Pédagogie en prose —
aucun scalaire de classement (≠ glossaire).
"""

from __future__ import annotations

from xerocr.evaluation.analysis import (
    ModernizedToken,
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


def _token_flow(token: ModernizedToken) -> str:
    """Une forme GT → ses variantes produites (chips, barre ∝ compte = taille)."""
    max_count = token.variants[0].count if token.variants else 1
    chips = "".join(
        f'<span class="wf-dst"><span class="wf-word">{escape(variant.form)}</span>'
        f'<span class="wf-bar" style="width:{round(variant.count / max_count * 40)}px">'
        f'</span><span class="wf-count">×{variant.count}</span></span>'
        for variant in token.variants
    )
    return (
        '<div class="wf-row">'
        f'<span class="wf-word wf-src">{escape(token.token)}</span>'
        f'<span class="wf-meta">{token.rate:.1%}</span>'
        f'<span class="wf-arrow">→</span>{chips}</div>'
    )


def _modernization_block(view: str, payload: TextualFidelityPayload) -> str:
    """Flux de modernisation (#17) : par pipeline, forme GT → variantes produites."""
    groups: list[str] = []
    for row in payload.pipelines:
        if not row.modernization:
            continue
        flows = "".join(_token_flow(token) for token in row.modernization)
        groups.append(
            f'<div class="cf-engine"><span class="cf-eng-name">'
            f"{escape(row.pipeline)}</span>"
            f'<div class="wflow">{flows}</div></div>'
        )
    if not groups:
        return ""
    return (
        f"<h3>{escape(view)} — modernisation lexicale</h3>\n"
        '<p class="muted">Formes historiques de la GT réécrites par le moteur '
        "(diagnostic de prompt LLM) : la forme attendue → les variantes produites "
        "(barre = fréquence ; taux de réécriture en regard ; « ∅ » = mot "
        "supprimé).</p>\n" + "".join(groups)
    )


def _block(view: str, payload: TextualFidelityPayload) -> str:
    rare_rows = "".join(_rare_row(row) for row in payload.pipelines)
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
    return rare_table + _modernization_block(view, payload)


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
