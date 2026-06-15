"""Section conformité HIPE : scores du scorer officiel + deltas (couche 7).

Rend le payload ``hipe`` en **lecture seule** : par pipeline, cMER/wMER
micro+macro (noms du scorer HIPE-OCRepair — la frontière de nommage, le
registre garde ``cmer``/``mer``), deltas de normalisation entre vues et
documents manquants. Chaque nombre porte son profil (SPEC_HIPE §7.2).
"""

from __future__ import annotations

from xerocr.evaluation.analysis import ConformityPayload
from xerocr.evaluation.result import RunResult
from xerocr.reports.html import escape, localized
from xerocr.reports.section import Html, SectionContext


def _cell(value: float | None, *, signed: bool = False) -> str:
    if value is None:
        return '<td class="disp muted">—</td>'
    text = f"{value:+.4f}" if signed else f"{value:.4f}"
    return f'<td class="disp">{text}</td>'


def _block(payload: ConformityPayload, lang: str) -> str:
    raw = escape(payload.raw_view) if payload.raw_view else "—"
    heritage = escape(payload.heritage_view) if payload.heritage_view else "—"
    rows = "".join(
        f'<tr><td class="eng-cell">{escape(row.pipeline)}</td>'
        + _cell(row.cmer_micro)
        + _cell(row.cmer_macro)
        + _cell(row.wmer_micro)
        + _cell(row.wmer_macro)
        + _cell(row.delta_norm, signed=True)
        + _cell(row.delta_heritage, signed=True)
        + f'<td class="disp">{row.n_missing}</td></tr>'
        for row in payload.pipelines
    )
    head = localized(
        lang,
        f"{escape(payload.hipe_view)} — scores HIPE-OCRepair",
        f"{escape(payload.hipe_view)} — HIPE-OCRepair scores",
    )
    prose = localized(
        lang,
        '<p class="muted">cMER/wMER = Match Error Rate (borné [0, 1] — '
        "comparable même pour un modèle génératif qui rallonge le texte), "
        "calculés sous le profil de normalisation du scorer officiel. "
        f"Δ norm = cmer({raw}) − cmer({escape(payload.hipe_view)}) : part "
        "d'erreur imputable à casse/ponctuation/formes mappées ; Δ heritage = "
        f"cmer({heritage}) − cmer({escape(payload.hipe_view)}) : part des seuls "
        "mappings patrimoniaux (œ/æ/ß/ꝛ…). « manquants » = documents sans "
        "sortie scorée sur cette vue.</p>\n",
        '<p class="muted">cMER/wMER = Match Error Rate (bounded to [0, 1] — '
        "comparable even for a generative model that lengthens the text), "
        "computed under the official scorer's normalization profile. "
        f"Δ norm = cmer({raw}) − cmer({escape(payload.hipe_view)}): share "
        "of error attributable to case/punctuation/mapped forms; Δ heritage = "
        f"cmer({heritage}) − cmer({escape(payload.hipe_view)}): share of the "
        'heritage mappings alone (œ/æ/ß/ꝛ…). "missing" = documents with no '
        "output scored on this view.</p>\n",
    )
    th_pipeline = localized(lang, "Pipeline", "Pipeline")
    th_missing = localized(lang, "manquants", "missing")
    return (
        f"<h3>{head}</h3>\n"
        f"{prose}"
        f'<table class="data">\n<thead><tr><th>{th_pipeline}</th>'
        '<th class="num-cell">cmer_micro</th><th class="num-cell">cmer_macro</th>'
        '<th class="num-cell">wmer_micro</th><th class="num-cell">wmer_macro</th>'
        '<th class="num-cell">Δ norm</th><th class="num-cell">Δ heritage</th>'
        f'<th class="num-cell">{th_missing}</th></tr></thead>\n'
        f"<tbody>{rows}</tbody>\n</table>\n"
    )


class ConformitySection:
    """Scores HIPE officiels (cmer/wmer micro+macro) + deltas de normalisation."""

    name = "conformity"
    requires: tuple[str, ...] = ()

    def render(self, result: RunResult, ctx: SectionContext) -> Html | None:
        blocks = [
            _block(analysis.payload, ctx.lang)
            for analysis in result.analyses
            if isinstance(analysis.payload, ConformityPayload)
        ]
        if not blocks:
            return None
        title = localized(ctx.lang, "Conformité HIPE", "HIPE conformity")
        return Html(f"<h2>{title}</h2>\n" + "".join(blocks))


__all__ = ["ConformitySection"]
