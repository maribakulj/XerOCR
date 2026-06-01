"""Section overview : bande de **readouts** (portée du corpus) + une table par
vue, pipelines × métriques, avec **data-bars** proportionnelles. Couche 7.

Le contenu reste piloté par les **vraies** métriques de ``RunResult`` (ce que le
moteur calcule : CER/WER/MER aujourd'hui) — **jamais** par les métriques que le
design *dessine* mais que le moteur ne produit pas encore (note d'archi S4.b :
pas de rapport en avance sur sa donnée). Les sections plus riches arrivent au fil
des métriques (T7).
"""

from __future__ import annotations

from xerocr.evaluation.result import MetricScore, PipelineResult, RunResult
from xerocr.reports.html import escape
from xerocr.reports.section import Html, SectionContext


def _format_value(score: MetricScore) -> str:
    return "—" if score.value is None else f"{score.value:.4f}"


def _views_in_order(pipelines: tuple[PipelineResult, ...]) -> tuple[str, ...]:
    ordered: list[str] = []
    for pipeline in pipelines:
        if pipeline.view not in ordered:
            ordered.append(pipeline.view)
    return tuple(ordered)


def _readout(label: str, value: int) -> str:
    return (
        f'<div class="readout"><span class="r-label">{escape(label)}</span>'
        f'<span class="r-value">{value}</span></div>'
    )


class OverviewSection:
    """Vue d'ensemble : readouts de portée + une table par vue (data-bars)."""

    name = "overview"
    requires: tuple[str, ...] = ()  # générique : affiche les métriques présentes

    def render(self, result: RunResult, ctx: SectionContext) -> Html | None:
        if not result.pipelines:
            return None
        views = _views_in_order(result.pipelines)
        n_pipelines = len({p.pipeline for p in result.pipelines})
        n_metrics = len({s.metric for p in result.pipelines for s in p.aggregate})
        parts: list[str] = [
            "<h2>Vue d'ensemble</h2>",
            f'<p class="muted">Corpus : {escape(result.manifest.corpus_name)}</p>',
            '<div class="readouts">',
            _readout("Documents", result.manifest.n_documents),
            _readout("Pipelines", n_pipelines),
            _readout("Vues", len(views)),
            _readout("Métriques", n_metrics),
            "</div>",
        ]
        for view_name in views:
            parts.append(_table_for_view(result, view_name))
        return Html("\n".join(parts) + "\n")


def _col_max(pipelines: list[PipelineResult], index: int) -> float:
    """Plus grande valeur (non ``None``) de la colonne métrique → échelle du bar."""
    values = [v for p in pipelines if (v := p.aggregate[index].value) is not None]
    return max(values) if values else 0.0


def _bar_cell(score: MetricScore, col_max: float) -> str:
    text = _format_value(score)
    if score.value is None or col_max <= 0:
        return f'<td class="databar"><span class="db-num">{text}</span></td>'
    width = round(score.value / col_max * 100)  # relatif à la colonne (déterministe)
    return (
        '<td class="databar">'
        f'<span class="db-fill" style="width:{width}%"></span>'
        f'<span class="db-num">{text}</span></td>'
    )


def _table_for_view(result: RunResult, view_name: str) -> str:
    pipelines = [p for p in result.pipelines if p.view == view_name]
    metrics = tuple(score.metric for score in pipelines[0].aggregate)
    header = "".join(f'<th class="num-cell">{escape(m)}</th>' for m in metrics)
    maxes = [_col_max(pipelines, i) for i in range(len(metrics))]
    body_rows: list[str] = []
    for pipeline in pipelines:
        cells = "".join(
            _bar_cell(score, maxes[i]) for i, score in enumerate(pipeline.aggregate)
        )
        body_rows.append(
            f'<tr><td class="eng-cell">{escape(pipeline.pipeline)}</td>{cells}</tr>'
        )
    return (
        f"<h2>Vue : {escape(view_name)}</h2>\n"
        f'<table class="data">\n<thead><tr><th>Pipeline</th>{header}</tr></thead>\n'
        f"<tbody>{''.join(body_rows)}</tbody>\n</table>"
    )


__all__ = ["OverviewSection"]
