"""Section économie : coûts estimés, débit effectif, Pareto (couche 7).

Rend les payloads ``economics`` de ``RunResult.analyses`` en **lecture seule**
(tout est calculé en couche 3 — anti data-layer). Chaque nombre est une
fonction auditable des mesures E1 + de la table de tarifs **datée** : si la
table est périmée au moment du run (``pricing_stale``), un avertissement
explicite est rendu — jamais un chiffre silencieusement périmé.
"""

from __future__ import annotations

from xerocr.evaluation.analysis import EconomicsPayload
from xerocr.evaluation.result import RunResult
from xerocr.reports.html import escape
from xerocr.reports.section import Html, SectionContext


def _fmt(value: float | None, pattern: str = "{:.4f}") -> str:
    return "—" if value is None else pattern.format(value)


def _fmt_int(value: int | None) -> str:
    return "—" if value is None else f"{value}"


def _block(view: str, payload: EconomicsPayload) -> str:
    rows: list[str] = []
    for row in payload.pipelines:
        rows.append(
            f'<tr><td class="eng-cell">{escape(row.pipeline)}</td>'
            f'<td class="disp">{_fmt(row.cer)}</td>'
            f'<td class="disp">{_fmt(row.duration_seconds, "{:.1f}")}</td>'
            f'<td class="disp">{_fmt_int(row.tokens_in)}</td>'
            f'<td class="disp">{_fmt_int(row.tokens_out)}</td>'
            f'<td class="disp">{_fmt(row.cost_eur)}</td>'
            f'<td class="eng-cell">{escape(row.basis)}</td>'
            f'<td class="disp">{_fmt(row.pages_per_hour, "{:.1f}")}</td>'
            f'<td class="disp">{_fmt(row.pages_per_hour_effective, "{:.1f}")}</td>'
            "</tr>"
        )
    stale = (
        '<p class="verdict sig">⚠ Table de tarifs périmée au moment du run '
        f"(valable jusqu'au {escape(payload.pricing_valid_until)}) — coûts à "
        "revalider.</p>\n"
        if payload.pricing_stale
        else ""
    )
    marginal = ""
    if payload.marginal:
        items = "".join(
            f'<tr><td class="eng-cell">{escape(m.pipeline)}</td>'
            f'<td class="eng-cell">{escape(m.baseline)}</td>'
            f'<td class="disp">{m.cost_delta_eur:+.4f}</td>'
            f'<td class="disp">{m.errors_avoided:+.1f}</td>'
            f'<td class="disp">{_fmt(m.eur_per_avoided_error)}</td></tr>'
            for m in payload.marginal
        )
        marginal = (
            "<h4>Coût marginal (vs pipeline le moins cher)</h4>\n"
            '<table class="data">\n<thead><tr><th>Pipeline</th><th>Référence</th>'
            f'<th class="num-cell">Δ coût ({escape(payload.currency)})</th>'
            '<th class="num-cell">erreurs évitées</th>'
            f'<th class="num-cell">{escape(payload.currency)}/erreur évitée</th>'
            f"</tr></thead>\n<tbody>{items}</tbody>\n</table>\n"
        )
    pareto = ""
    if payload.pareto_cost or payload.pareto_speed:
        cost_names = ", ".join(escape(n) for n in payload.pareto_cost) or "—"
        speed_names = ", ".join(escape(n) for n in payload.pareto_speed) or "—"
        pareto = (
            f'<p class="muted">Front de Pareto {escape(payload.metric)} × coût : '
            f"{cost_names} · {escape(payload.metric)} × durée : {speed_names}.</p>\n"
        )
    return (
        f"<h3>{escape(view)} — coûts &amp; débit</h3>\n"
        + stale
        + '<p class="muted">Coûts <strong>indicatifs</strong> : temps machine '
        f"(durée mesurée × {payload.hourly_rate_eur:g} "
        f"{escape(payload.currency)}/h) + jetons cloud au tarif de la table "
        f"(valable jusqu'au {escape(payload.pricing_valid_until)}) ; débit "
        "effectif corrigé du temps de relecture "
        f"({payload.time_per_error_seconds:g} s/erreur).</p>\n"
        '<table class="data">\n'
        "<thead><tr><th>Pipeline</th>"
        f'<th class="num-cell">{escape(payload.metric)}</th>'
        '<th class="num-cell">durée (s)</th>'
        '<th class="num-cell">jetons in</th><th class="num-cell">jetons out</th>'
        f'<th class="num-cell">coût ({escape(payload.currency)})</th>'
        "<th>base</th>"
        '<th class="num-cell">pages/h</th>'
        '<th class="num-cell">pages/h effectif</th></tr></thead>\n'
        f"<tbody>{''.join(rows)}</tbody>\n</table>\n"
        + pareto
        + marginal
    )


class EconomicsSection:
    """Coûts estimés, débit effectif et fronts de Pareto, par vue."""

    name = "economics"
    requires: tuple[str, ...] = ()

    def render(self, result: RunResult, ctx: SectionContext) -> Html | None:
        blocks = [
            _block(analysis.view, analysis.payload)
            for analysis in result.analyses
            if isinstance(analysis.payload, EconomicsPayload)
        ]
        if not blocks:
            return None
        return Html("<h2>Économie</h2>\n" + "".join(blocks))


__all__ = ["EconomicsSection"]
