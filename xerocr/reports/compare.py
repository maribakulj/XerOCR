"""Comparaison de deux ``RunResult`` (couche 7) → rapport HTML de deltas.

Hors ``Protocol Section`` (qui ne prend qu'**un** résultat) : ``compare`` met deux
runs côte à côte et calcule, par ``(pipeline, vue, métrique)``, le delta
``B − A``. Le rapport reste **autonome** (assembleur ``render_document``).
"""

from __future__ import annotations

from dataclasses import dataclass

from xerocr.evaluation.result import RunResult
from xerocr.reports.html import escape, render_document
from xerocr.reports.section import Html

_Key = tuple[str, str, str]


@dataclass(frozen=True)
class MetricDelta:
    """Valeur d'une métrique dans deux runs + leur écart (``B − A``)."""

    pipeline: str
    view: str
    metric: str
    value_a: float | None
    value_b: float | None
    delta: float | None


def compare_runs(run_a: RunResult, run_b: RunResult) -> tuple[MetricDelta, ...]:
    """Aligne deux runs par ``(pipeline, vue, métrique)`` et calcule les deltas."""
    index_a = _index(run_a)
    index_b = _index(run_b)
    deltas: list[MetricDelta] = []
    for key in sorted(set(index_a) | set(index_b)):
        value_a = index_a.get(key)
        value_b = index_b.get(key)
        delta = (
            value_b - value_a
            if value_a is not None and value_b is not None
            else None
        )
        deltas.append(
            MetricDelta(
                pipeline=key[0],
                view=key[1],
                metric=key[2],
                value_a=value_a,
                value_b=value_b,
                delta=delta,
            )
        )
    return tuple(deltas)


def _index(result: RunResult) -> dict[_Key, float | None]:
    return {
        (pipeline.pipeline, pipeline.view, score.metric): score.value
        for pipeline in result.pipelines
        for score in pipeline.aggregate
    }


def _format(value: float | None) -> str:
    return "—" if value is None else f"{value:.4f}"


def _format_delta(value: float | None) -> str:
    return "—" if value is None else f"{value:+.4f}"


def render_comparison(
    run_a: RunResult,
    run_b: RunResult,
    *,
    title: str = "XerOCR — comparaison de runs",
) -> str:
    """Rend un rapport HTML autonome des deltas entre deux runs."""
    rows = "".join(
        f"<tr><td>{escape(delta.pipeline)}</td><td>{escape(delta.view)}</td>"
        f"<td>{escape(delta.metric)}</td>"
        f'<td class="num">{_format(delta.value_a)}</td>'
        f'<td class="num">{_format(delta.value_b)}</td>'
        f'<td class="num">{_format_delta(delta.delta)}</td></tr>'
        for delta in compare_runs(run_a, run_b)
    )
    # NB : le sens « mieux » dépend de la métrique. Les métriques livrées
    # (CER/WER/MER) sont **toutes** des taux d'erreur → on l'annonce explicitement
    # plutôt qu'en supposant l'universalité. Porter `higher_is_better` jusque dans
    # `RunResult` est différé tant qu'aucune métrique « plus haut = mieux » n'existe.
    body = Html(
        f'<p class="muted">A = {escape(run_a.manifest.run_id)} · '
        f"B = {escape(run_b.manifest.run_id)} · Δ = B − A "
        "(taux d'erreur CER/WER/MER : Δ &lt; 0 = amélioration).</p>\n"
        "<table>\n<thead><tr><th>Pipeline</th><th>Vue</th><th>Métrique</th>"
        "<th>A</th><th>B</th><th>Δ</th></tr></thead>\n"
        f"<tbody>{rows}</tbody>\n</table>\n"
    )
    return render_document(title, body)


__all__ = ["MetricDelta", "compare_runs", "render_comparison"]
