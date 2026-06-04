"""Section synthèse : **verdict factuel chiffré** par vue (couche 7).

Pour chaque vue dotée de la métrique phare (**CER**, plus-bas-est-meilleur),
nomme le **meilleur pipeline**, son CER, l'**écart** (Δ CER) au pipeline suivant
et si la différence inter-moteurs est **statistiquement significative** (reprise
de ``RunResult.cross_engine``). Aucun LLM, aucune prose générée : les noms sont
*verbatim* du ``RunResult`` et chaque nombre est une **fonction auditable** de ses
valeurs (minimum, soustraction, p-value) — invariant anti-hallucination (§12),
moteur narratif supprimé (§6). Gatée sur ``cer`` (``requires``) : ``None`` si
aucune vue ne porte de CER.
"""

from __future__ import annotations

from xerocr.evaluation.result import MetricScore, RunResult
from xerocr.reports.html import escape
from xerocr.reports.section import Html, SectionContext
from xerocr.reports.sections._tables import ordered_unique

#: Métrique phare du verdict (plus bas = meilleur) ; la section est *gatée* dessus.
_PRIMARY_METRIC = "cer"


def _cer(scores: tuple[MetricScore, ...]) -> float | None:
    for score in scores:
        if score.metric == _PRIMARY_METRIC:
            return score.value
    return None


def _ranked_by_cer(result: RunResult, view: str) -> list[tuple[float, str]]:
    """Pipelines de la vue ayant un CER, triés croissant (meilleur d'abord).

    Tri par ``(cer, pipeline)`` → **déterministe** même à égalité de CER.
    """
    pairs: list[tuple[float, str]] = []
    for pipeline in result.pipelines:
        if pipeline.view != view:
            continue
        cer = _cer(pipeline.aggregate)
        if cer is not None:
            pairs.append((cer, pipeline.pipeline))
    return sorted(pairs, key=lambda item: (item[0], item[1]))


def _significance_p(result: RunResult, view: str) -> float | None:
    """p-value inter-moteurs (``view`` × CER) ; ``None`` si absente."""
    for score in result.cross_engine:
        parts = score.metric.split(":")
        if len(parts) >= 2 and parts[0] == view and parts[1] == _PRIMARY_METRIC:
            return score.value
    return None


def _verdict(p_value: float | None) -> tuple[str, str]:
    """(libellé, classe CSS) — significatif si p < 0,05 ; ``None`` → tiret."""
    if p_value is None:
        return "—", ""
    if p_value < 0.05:
        return f"significatif (p={p_value:.4f})", " sig"
    return f"non sig. (p={p_value:.4f})", ""


class SynthesisSection:
    """Verdict factuel : meilleur pipeline par vue (CER), écart, significativité."""

    name = "synthesis"
    requires: tuple[str, ...] = (_PRIMARY_METRIC,)

    def render(self, result: RunResult, ctx: SectionContext) -> Html | None:
        rows: list[str] = []
        for view in ordered_unique(p.view for p in result.pipelines):
            ranked = _ranked_by_cer(result, view)
            if not ranked:
                continue
            best_cer, best = ranked[0]
            if len(ranked) >= 2:
                runner_cer, runner = ranked[1]
                delta = f"{runner_cer - best_cer:.4f}"
                runner_label = escape(runner)
                label, css = _verdict(_significance_p(result, view))
            else:
                delta, runner_label, label, css = "—", "—", "—", ""
            rows.append(
                f'<tr><td class="eng-cell">{escape(view)}</td>'
                f'<td class="eng-cell">{escape(best)}</td>'
                f'<td class="disp">{best_cer:.4f}</td>'
                f'<td class="eng-cell">{runner_label}</td>'
                f'<td class="disp">{delta}</td>'
                f'<td class="verdict{css}">{label}</td></tr>'
            )
        if not rows:
            return None
        return Html(
            "<h2>Synthèse</h2>\n"
            '<p class="muted">Meilleur pipeline par vue selon le CER '
            "(plus bas = meilleur) ; écart Δ CER au pipeline suivant et "
            "significativité de la différence inter-moteurs (p &lt; 0,05).</p>\n"
            '<table class="data">\n'
            "<thead><tr><th>Vue</th><th>Meilleur pipeline</th>"
            '<th class="num-cell">CER</th><th>2ᵉ</th>'
            '<th class="num-cell">Δ CER</th><th>écart</th></tr></thead>\n'
            f"<tbody>{''.join(rows)}</tbody>\n</table>\n"
        )


__all__ = ["SynthesisSection"]
