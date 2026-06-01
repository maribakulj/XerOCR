"""Section significativité inter-moteurs : rend ``RunResult.cross_engine``.

Rend visible ce que la passe inter-moteurs (couche 3) a calculé : pour chaque
``vue:métrique``, la p-value d'une différence entre pipelines. ``None`` si la
section est inapplicable (aucun résultat inter-moteurs).
"""

from __future__ import annotations

from xerocr.evaluation.result import MetricScore, RunResult
from xerocr.reports.html import escape
from xerocr.reports.section import Html, SectionContext


def _format_p(score: MetricScore) -> str:
    return "—" if score.value is None else f"{score.value:.4f}"


class CrossEngineSection:
    """P-values de différence inter-moteurs (Wilcoxon / Friedman)."""

    name = "cross_engine"
    requires: tuple[str, ...] = ()

    def render(self, result: RunResult, ctx: SectionContext) -> Html | None:
        if not result.cross_engine:
            return None
        rows = "".join(
            f"<tr><td>{escape(score.metric)}</td>"
            f'<td class="num">{_format_p(score)}</td>'
            f'<td class="num">{score.support}</td></tr>'
            for score in result.cross_engine
        )
        return Html(
            "<h2>Significativité inter-moteurs</h2>\n"
            '<p class="muted">p-value d\'une différence entre pipelines '
            "(Wilcoxon / Friedman) ; significatif si p &lt; 0,05.</p>\n"
            "<table>\n<thead><tr><th>Comparaison</th><th>p-value</th>"
            "<th>n</th></tr></thead>\n"
            f"<tbody>{rows}</tbody>\n</table>\n"
        )


__all__ = ["CrossEngineSection"]
