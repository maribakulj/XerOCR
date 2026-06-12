"""Section conformité HIPE : scores du scorer officiel + deltas (couche 7).

Rend le payload ``hipe`` en **lecture seule** : par pipeline, cMER/wMER
micro+macro (noms du scorer HIPE-OCRepair — la frontière de nommage, le
registre garde ``cmer``/``mer``), deltas de normalisation entre vues et
documents manquants. Chaque nombre porte son profil (SPEC_HIPE §7.2).
"""

from __future__ import annotations

from xerocr.evaluation.analysis import ConformityPayload
from xerocr.evaluation.result import RunResult
from xerocr.reports.html import escape
from xerocr.reports.section import Html, SectionContext


def _cell(value: float | None, *, signed: bool = False) -> str:
    if value is None:
        return '<td class="disp muted">—</td>'
    text = f"{value:+.4f}" if signed else f"{value:.4f}"
    return f'<td class="disp">{text}</td>'


def _block(payload: ConformityPayload) -> str:
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
    return (
        f"<h3>{escape(payload.hipe_view)} — scores HIPE-OCRepair</h3>\n"
        '<p class="muted">cMER/wMER = Match Error Rate (borné [0, 1] — '
        "comparable même pour un modèle génératif qui rallonge le texte), "
        "calculés sous le profil de normalisation du scorer officiel. "
        f"Δ norm = cmer({raw}) − cmer({escape(payload.hipe_view)}) : part "
        "d'erreur imputable à casse/ponctuation/formes mappées ; Δ heritage = "
        f"cmer({heritage}) − cmer({escape(payload.hipe_view)}) : part des seuls "
        "mappings patrimoniaux (œ/æ/ß/ꝛ…). « manquants » = documents sans "
        "sortie scorée sur cette vue.</p>\n"
        '<table class="data">\n<thead><tr><th>Pipeline</th>'
        '<th class="num-cell">cmer_micro</th><th class="num-cell">cmer_macro</th>'
        '<th class="num-cell">wmer_micro</th><th class="num-cell">wmer_macro</th>'
        '<th class="num-cell">Δ norm</th><th class="num-cell">Δ heritage</th>'
        '<th class="num-cell">manquants</th></tr></thead>\n'
        f"<tbody>{rows}</tbody>\n</table>\n"
    )


class ConformitySection:
    """Scores HIPE officiels (cmer/wmer micro+macro) + deltas de normalisation."""

    name = "conformity"
    requires: tuple[str, ...] = ()

    def render(self, result: RunResult, ctx: SectionContext) -> Html | None:
        blocks = [
            _block(analysis.payload)
            for analysis in result.analyses
            if isinstance(analysis.payload, ConformityPayload)
        ]
        if not blocks:
            return None
        return Html("<h2>Conformité HIPE</h2>\n" + "".join(blocks))


__all__ = ["ConformitySection"]
