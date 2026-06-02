"""Section significativité inter-moteurs : rend ``RunResult.cross_engine`` au design.

Pour chaque ``vue:métrique``, la p-value d'une différence entre pipelines
(Wilcoxon / Friedman) + un **verdict factuel** (significatif si p < 0,05). Le
verdict est une **fonction auditable** de la p-value — une étiquette, pas de la
prose (narratif supprimé, ``CLAUDE.md`` §6). ``None`` si inapplicable (aucun
résultat inter-moteurs, ou sous le plancher de puissance).
"""

from __future__ import annotations

from xerocr.evaluation.result import RunResult
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


class CrossEngineSection:
    """P-values de différence inter-moteurs (Wilcoxon / Friedman) + verdict."""

    name = "cross_engine"
    requires: tuple[str, ...] = ()

    def render(self, result: RunResult, ctx: SectionContext) -> Html | None:
        if not result.cross_engine:
            return None
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
        return Html(
            "<h2>Significativité inter-moteurs</h2>\n"
            '<p class="muted">p-value d\'une différence entre pipelines '
            "(Wilcoxon / Friedman) ; significatif si p &lt; 0,05.</p>\n"
            '<table class="data">\n'
            "<thead><tr><th>Vue</th><th>Métrique</th>"
            '<th class="num-cell">p-value</th><th class="num-cell">n</th>'
            "<th>verdict</th></tr></thead>\n"
            f"<tbody>{''.join(body)}</tbody>\n</table>\n"
        )


__all__ = ["CrossEngineSection"]
