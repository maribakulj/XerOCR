"""Section significativité inter-moteurs : rend ``RunResult.cross_engine`` au design.

Pour chaque ``vue:métrique``, la p-value d'une différence entre pipelines
(Wilcoxon / Friedman) + un **verdict factuel** (significatif si p < 0,05). Le
verdict est une **fonction auditable** de la p-value — une étiquette, pas de la
prose (narratif supprimé, ``CLAUDE.md`` §6). ``None`` si inapplicable (aucun
résultat inter-moteurs, ou sous le plancher de puissance).

Sous le tableau des p-values, la section **lit** (sans recalculer) les payloads
``inference`` de ``RunResult.analyses`` : rangs moyens, distance critique de
Nemenyi (correction multi-comparaisons), groupes statistiquement
indiscernables, et IC bootstrap à 95 % par pipeline.
"""

from __future__ import annotations

from collections.abc import Mapping

from xerocr.evaluation.analysis import InferencePayload
from xerocr.evaluation.result import RunResult
from xerocr.reports.engine_badges import engine_cell, engine_order
from xerocr.reports.html import escape
from xerocr.reports.section import Html, SectionContext


def _format_p(value: float | None) -> str:
    return "—" if value is None else f"{value:.4f}"


def _split_key(key: str) -> tuple[str, str]:
    """``"text:cer:significance_p"`` → ``("text", "cer")`` ; sinon (clé, "")."""
    parts = key.split(":")
    if len(parts) >= 2:
        return parts[0], parts[1]
    return key, ""


def _verdict(value: float | None) -> tuple[str, str]:
    """(libellé, classe CSS) — significatif si p < 0,05 ; ``None`` → tiret."""
    if value is None:
        return "—", ""
    if value < 0.05:
        return "significatif", " sig"
    return "non sig.", ""


def _inference_block(
    view: str, payload: InferencePayload, order: Mapping[str, int]
) -> str:
    """Rendu d'un payload ``inference`` : rangs, Nemenyi, IC bootstrap."""
    rows: list[str] = []
    intervals = {item.pipeline: item for item in payload.intervals}
    for rank in payload.mean_ranks:
        interval = intervals.get(rank.pipeline)
        ic = (
            f"[{interval.lower:.4f} ; {interval.upper:.4f}]"
            if interval is not None
            else "—"
        )
        mean = f"{interval.mean:.4f}" if interval is not None else "—"
        badge = engine_cell(rank.pipeline, order.get(rank.pipeline, 0))
        rows.append(
            f'<tr><td class="eng-cell">{badge}</td>'
            f'<td class="disp">{rank.mean_rank:.3f}</td>'
            f'<td class="disp">{mean}</td>'
            f'<td class="disp">{ic}</td></tr>'
        )
    if payload.critical_distance is not None:
        groups = " · ".join(
            "{" + ", ".join(escape(name) for name in group) + "}"
            for group in payload.tied_groups
        )
        extrapolated = " (q extrapolé)" if payload.q_alpha_extrapolated else ""
        nemenyi = (
            f'<p class="muted">Nemenyi (α={payload.alpha:g}) : distance '
            f"critique CD = {payload.critical_distance:.4f}{extrapolated} ; "
            f"groupes indiscernables : {groups}.</p>\n"
        )
    else:
        nemenyi = (
            '<p class="muted">2 pipelines : le verdict apparié est la p-value '
            "Wilcoxon ci-dessus (pas de post-hoc).</p>\n"
        )
    return (
        f"<h3>{escape(view)} · {escape(payload.metric)} — rangs &amp; IC "
        f"(n={payload.n_documents})</h3>\n"
        + nemenyi
        + '<table class="data">\n'
        "<thead><tr><th>Pipeline</th>"
        '<th class="num-cell">rang moyen</th>'
        '<th class="num-cell">moyenne</th>'
        '<th class="num-cell">IC 95 % (bootstrap)</th></tr></thead>\n'
        f"<tbody>{''.join(rows)}</tbody>\n</table>\n"
    )


class CrossEngineSection:
    """P-values de différence inter-moteurs (Wilcoxon / Friedman) + verdict."""

    name = "cross_engine"
    requires: tuple[str, ...] = ()

    def render(self, result: RunResult, ctx: SectionContext) -> Html | None:
        if not result.cross_engine:
            return None
        order = engine_order(p.pipeline for p in result.pipelines)
        body: list[str] = []
        for score in result.cross_engine:
            view, metric = _split_key(score.metric)
            label, css = _verdict(score.value)
            body.append(
                f'<tr><td class="eng-cell">{escape(view)}</td>'
                f'<td class="eng-cell">{escape(metric)}</td>'
                f'<td class="disp">{_format_p(score.value)}</td>'
                f'<td class="disp">{score.support}</td>'
                f'<td class="verdict{css}">{label}</td></tr>'
            )
        blocks = "".join(
            _inference_block(analysis.view, analysis.payload, order)
            for analysis in result.analyses
            if isinstance(analysis.payload, InferencePayload)
        )
        return Html(
            "<h2>Significativité inter-moteurs</h2>\n"
            '<p class="muted">p-value d\'une différence entre pipelines '
            "(Wilcoxon / Friedman) ; significatif si p &lt; 0,05.</p>\n"
            '<table class="data">\n'
            "<thead><tr><th>Vue</th><th>Métrique</th>"
            '<th class="num-cell">p-value</th><th class="num-cell">n</th>'
            "<th>verdict</th></tr></thead>\n"
            f"<tbody>{''.join(body)}</tbody>\n</table>\n"
            + blocks
        )


__all__ = ["CrossEngineSection"]
