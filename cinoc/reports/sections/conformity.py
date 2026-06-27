"""Section conformité HIPE : scores du scorer officiel + deltas (couche 7).

Rend le payload ``hipe`` en **lecture seule** : par pipeline, cMER/wMER
micro+macro (noms du scorer HIPE-OCRepair — la frontière de nommage, le
registre garde ``cmer``/``mer``), deltas de normalisation entre vues et
documents manquants. Chaque nombre porte son profil (SPEC_HIPE §7.2).
"""

from __future__ import annotations

from cinoc.evaluation.analysis import ConformityPayload, PipelineConformity
from cinoc.evaluation.result import RunResult
from cinoc.reports.engine_badges import engine_cell, engine_order
from cinoc.reports.html import escape, localized, view_label
from cinoc.reports.section import Html, SectionContext


def _cell(value: float | None, *, signed: bool = False) -> str:
    if value is None:
        return '<td class="disp muted">—</td>'
    text = f"{value:+.4f}" if signed else f"{value:.4f}"
    return f'<td class="disp">{text}</td>'


def _block(payload: ConformityPayload, lang: str, order: dict[str, int]) -> str:
    # Deltas de normalisation = uniquement quand une vraie ancre HIPE + vues
    # brute/heritage existent ; sinon on montre cMER/wMER micro·macro seuls.
    has_deltas = payload.raw_view is not None or payload.heritage_view is not None
    view = escape(view_label(payload.hipe_view, lang))

    def _row(row: PipelineConformity) -> str:
        deltas = (
            _cell(row.delta_norm, signed=True) + _cell(row.delta_heritage, signed=True)
            if has_deltas
            else ""
        )
        return (
            f'<tr><td class="eng-cell">'
            f"{engine_cell(row.pipeline, order.get(row.pipeline, 0))}</td>"
            + _cell(row.cmer_micro) + _cell(row.cmer_macro)
            + _cell(row.wmer_micro) + _cell(row.wmer_macro)
            + deltas
            + f'<td class="disp">{row.n_missing}</td></tr>'
        )

    rows = "".join(_row(row) for row in payload.pipelines)
    if has_deltas:
        raw = escape(payload.raw_view) if payload.raw_view else "—"
        heritage = escape(payload.heritage_view) if payload.heritage_view else "—"
        head = localized(
            lang,
            f"{view} — scores HIPE-OCRepair",
            f"{view} — HIPE-OCRepair scores",
        )
        prose = localized(
            lang,
            '<p class="muted">cMER/wMER = Match Error Rate (borné [0, 1] — '
            "comparable même pour un modèle génératif qui rallonge le texte). "
            f"Δ norm = cmer({raw}) − cmer({view}) : part d'erreur imputable à "
            f"casse/ponctuation/formes mappées ; Δ heritage = cmer({heritage}) − "
            f"cmer({view}) : mappings patrimoniaux seuls (œ/æ/ß/ꝛ…). "
            "« manquants » = documents sans sortie scorée.</p>\n",
            '<p class="muted">cMER/wMER = Match Error Rate (bounded [0, 1] — '
            "comparable even for a generative model). "
            f"Δ norm = cmer({raw}) − cmer({view}); Δ heritage = cmer({heritage}) − "
            f"cmer({view}). \"missing\" = documents with no scored output.</p>\n",
        )
        delta_th = (
            '<th class="num-cell">Δ norm</th><th class="num-cell">Δ heritage</th>'
        )
    else:
        head = f"{view} — cMER · wMER (micro · macro)"
        prose = localized(
            lang,
            '<p class="muted">cMER/wMER = Match Error Rate <b>borné [0, 1]</b> '
            "(comparable même pour un modèle génératif qui rallonge le texte, là "
            "où le CER peut dépasser 100 %). <b>micro</b> = agrégat corpus "
            "(Σ erreurs / Σ dénominateurs) ; <b>macro</b> = moyenne des taux "
            "par document. « manquants » = documents sans sortie scorée.</p>\n",
            '<p class="muted">cMER/wMER = Match Error Rate <b>bounded [0, 1]</b> '
            "(comparable even for a generative model, where CER can exceed 100%). "
            "<b>micro</b> = corpus aggregate (Σ errors / Σ denominators); "
            "<b>macro</b> = mean of per-document rates. \"missing\" = documents "
            "with no scored output.</p>\n",
        )
        delta_th = ""
    th_pipeline = localized(lang, "Pipeline", "Pipeline")
    th_missing = localized(lang, "manquants", "missing")
    return (
        f"<h3>{head}</h3>\n"
        f"{prose}"
        f'<table class="data">\n<thead><tr><th>{th_pipeline}</th>'
        '<th class="num-cell">cmer_micro</th><th class="num-cell">cmer_macro</th>'
        '<th class="num-cell">wmer_micro</th><th class="num-cell">wmer_macro</th>'
        f"{delta_th}"
        f'<th class="num-cell">{th_missing}</th></tr></thead>\n'
        f"<tbody>{rows}</tbody>\n</table>\n"
    )


class ConformitySection:
    """Scores HIPE officiels (cmer/wmer micro+macro) + deltas de normalisation."""

    name = "conformity"
    requires: tuple[str, ...] = ()

    def render(self, result: RunResult, ctx: SectionContext) -> Html | None:
        order = engine_order(p.pipeline for p in result.pipelines)
        blocks = [
            _block(analysis.payload, ctx.lang, order)
            for analysis in result.analyses
            if isinstance(analysis.payload, ConformityPayload)
        ]
        if not blocks:
            return None
        is_hipe = any(
            isinstance(a.payload, ConformityPayload)
            and (a.payload.raw_view is not None or a.payload.heritage_view is not None)
            for a in result.analyses
        )
        title = (
            localized(ctx.lang, "Conformité HIPE", "HIPE conformity")
            if is_hipe
            else localized(ctx.lang, "Précision bornée (cMER · wMER)",
                           "Bounded accuracy (cMER · wMER)")
        )
        return Html(f"<h2>{title}</h2>\n" + "".join(blocks))


__all__ = ["ConformitySection"]
