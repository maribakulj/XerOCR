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
from xerocr.reports.html import escape, localized
from xerocr.reports.section import Html, SectionContext


def _fmt(value: float | None, pattern: str = "{:.4f}") -> str:
    return "—" if value is None else pattern.format(value)


def _fmt_int(value: int | None) -> str:
    return "—" if value is None else f"{value}"


def _block(view: str, payload: EconomicsPayload, lang: str) -> str:
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
        localized(
            lang,
            '<p class="verdict sig">⚠ Table de tarifs périmée au moment du run '
            f"(valable jusqu'au {escape(payload.pricing_valid_until)}) — coûts à "
            "revalider.</p>\n",
            '<p class="verdict sig">⚠ Pricing table stale at run time '
            f"(valid until {escape(payload.pricing_valid_until)}) — costs to "
            "revalidate.</p>\n",
        )
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
        marginal_head = localized(
            lang,
            "Coût marginal (vs pipeline le moins cher)",
            "Marginal cost (vs cheapest pipeline)",
        )
        th_pipeline = localized(lang, "Pipeline", "Pipeline")
        th_baseline = localized(lang, "Référence", "Baseline")
        th_cost_delta = localized(
            lang,
            f"Δ coût ({escape(payload.currency)})",
            f"Δ cost ({escape(payload.currency)})",
        )
        th_errors_avoided = localized(lang, "erreurs évitées", "errors avoided")
        th_per_avoided = localized(
            lang,
            f"{escape(payload.currency)}/erreur évitée",
            f"{escape(payload.currency)}/avoided error",
        )
        marginal = (
            f"<h4>{marginal_head}</h4>\n"
            f'<table class="data">\n<thead><tr><th>{th_pipeline}</th>'
            f"<th>{th_baseline}</th>"
            f'<th class="num-cell">{th_cost_delta}</th>'
            f'<th class="num-cell">{th_errors_avoided}</th>'
            f'<th class="num-cell">{th_per_avoided}</th>'
            f"</tr></thead>\n<tbody>{items}</tbody>\n</table>\n"
        )
    pareto = ""
    if payload.pareto_cost or payload.pareto_speed:
        cost_names = ", ".join(escape(n) for n in payload.pareto_cost) or "—"
        speed_names = ", ".join(escape(n) for n in payload.pareto_speed) or "—"
        pareto = localized(
            lang,
            f'<p class="muted">Front de Pareto {escape(payload.metric)} × coût : '
            f"{cost_names} · {escape(payload.metric)} × durée : {speed_names}.</p>\n",
            f'<p class="muted">Pareto front {escape(payload.metric)} × cost: '
            f"{cost_names} · {escape(payload.metric)} × duration: {speed_names}.</p>\n",
        )
    head = localized(
        lang,
        f"{escape(view)} — coûts &amp; débit",
        f"{escape(view)} — costs &amp; throughput",
    )
    prose = localized(
        lang,
        '<p class="muted">Coûts <strong>indicatifs</strong> : temps machine '
        f"(durée mesurée × {payload.hourly_rate_eur:g} "
        f"{escape(payload.currency)}/h) + jetons cloud au tarif de la table "
        f"(valable jusqu'au {escape(payload.pricing_valid_until)}) ; débit "
        "effectif corrigé du temps de relecture "
        f"({payload.time_per_error_seconds:g} s/erreur).</p>\n",
        '<p class="muted">Costs are <strong>indicative</strong>: machine time '
        f"(measured duration × {payload.hourly_rate_eur:g} "
        f"{escape(payload.currency)}/h) + cloud tokens at the table's rate "
        f"(valid until {escape(payload.pricing_valid_until)}); effective "
        "throughput corrected for proofreading time "
        f"({payload.time_per_error_seconds:g} s/error).</p>\n",
    )
    th_pipeline = localized(lang, "Pipeline", "Pipeline")
    th_duration = localized(lang, "durée (s)", "duration (s)")
    th_tokens_in = localized(lang, "jetons in", "tokens in")
    th_tokens_out = localized(lang, "jetons out", "tokens out")
    th_cost = localized(
        lang,
        f"coût ({escape(payload.currency)})",
        f"cost ({escape(payload.currency)})",
    )
    th_basis = localized(lang, "base", "basis")
    th_pages_per_hour = localized(lang, "pages/h", "pages/h")
    th_pages_per_hour_eff = localized(
        lang, "pages/h effectif", "pages/h effective"
    )
    return (
        f"<h3>{head}</h3>\n"
        + stale
        + prose
        + '<table class="data">\n'
        f"<thead><tr><th>{th_pipeline}</th>"
        f'<th class="num-cell">{escape(payload.metric)}</th>'
        f'<th class="num-cell">{th_duration}</th>'
        f'<th class="num-cell">{th_tokens_in}</th>'
        f'<th class="num-cell">{th_tokens_out}</th>'
        f'<th class="num-cell">{th_cost}</th>'
        f"<th>{th_basis}</th>"
        f'<th class="num-cell">{th_pages_per_hour}</th>'
        f'<th class="num-cell">{th_pages_per_hour_eff}</th></tr></thead>\n'
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
            _block(analysis.view, analysis.payload, ctx.lang)
            for analysis in result.analyses
            if isinstance(analysis.payload, EconomicsPayload)
        ]
        if not blocks:
            return None
        title = localized(ctx.lang, "Économie", "Economics")
        return Html(f"<h2>{title}</h2>\n" + "".join(blocks))


__all__ = ["EconomicsSection"]
