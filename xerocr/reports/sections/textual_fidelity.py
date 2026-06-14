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
from xerocr.reports.html import escape, localized
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


def _modernization_block(
    view: str, payload: TextualFidelityPayload, lang: str
) -> str:
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
    head = localized(
        lang,
        f"{escape(view)} — modernisation lexicale",
        f"{escape(view)} — lexical modernization",
    )
    prose = localized(
        lang,
        '<p class="muted">Formes historiques de la GT réécrites par le moteur '
        "(diagnostic de prompt LLM) : la forme attendue → les variantes produites "
        "(barre = fréquence ; taux de réécriture en regard ; « ∅ » = mot "
        "supprimé).</p>\n",
        '<p class="muted">Historical GT forms rewritten by the engine '
        "(LLM prompt diagnostic): the expected form → the produced variants "
        "(bar = frequency; rewrite rate alongside; “∅” = deleted "
        "word).</p>\n",
    )
    return f"<h3>{head}</h3>\n" + prose + "".join(groups)


def _block(view: str, payload: TextualFidelityPayload, lang: str) -> str:
    rare_rows = "".join(_rare_row(row) for row in payload.pipelines)
    head = localized(
        lang,
        f"{escape(view)} — rappel des tokens rares "
        f"(≤ {payload.max_freq} occurrence(s))",
        f"{escape(view)} — rare-token recall "
        f"(≤ {payload.max_freq} occurrence(s))",
    )
    prose = localized(
        lang,
        '<p class="muted">Les tokens rares (noms propres, toponymes, termes — '
        "hapax et dis legomena du corpus) pèsent en indexation prosopographique "
        "mais sont noyés dans le CER global. Rappel = part des occurrences rares "
        "de la GT retrouvées (multiset).</p>\n",
        '<p class="muted">Rare tokens (proper nouns, toponyms, terms — '
        "corpus hapax and dis legomena) matter for prosopographic indexing "
        "but are drowned out in the global CER. Recall = share of rare GT "
        "occurrences recovered (multiset).</p>\n",
    )
    th_pipeline = localized(lang, "Pipeline", "Pipeline")
    th_recalled_total = localized(lang, "rappelés/total", "recalled/total")
    th_recall = localized(lang, "rappel", "recall")
    th_missed = localized(lang, "manqués (échantillon)", "missed (sample)")
    rare_table = (
        f"<h3>{head}</h3>\n"
        + prose
        + '<table class="data">\n<thead><tr>'
        f"<th>{th_pipeline}</th>"
        f'<th class="num-cell">{th_recalled_total}</th>'
        f'<th class="num-cell">{th_recall}</th>'
        f"<th>{th_missed}</th></tr></thead>\n"
        f"<tbody>{rare_rows}</tbody>\n</table>\n"
    )
    return rare_table + _modernization_block(view, payload, lang)


class TextualFidelitySection:
    """Tokens rares + modernisation lexicale, par pipeline (lecture seule)."""

    name = "textual_fidelity"
    requires: tuple[str, ...] = ()

    def render(self, result: RunResult, ctx: SectionContext) -> Html | None:
        blocks = [
            _block(analysis.view, analysis.payload, ctx.lang)
            for analysis in result.analyses
            if isinstance(analysis.payload, TextualFidelityPayload)
        ]
        if not blocks:
            return None
        title = localized(ctx.lang, "Fidélité textuelle", "Textual fidelity")
        return Html(f"<h2>{title}</h2>\n" + "".join(blocks))


__all__ = ["TextualFidelitySection"]
