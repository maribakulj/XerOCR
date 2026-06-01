"""Section overview : bande de **readouts** (portée du corpus) + une table par
vue, pipelines × métriques, avec **data-bars** proportionnelles. Couche 7.

Le contenu reste piloté par les **vraies** métriques de ``RunResult`` (ce que le
moteur calcule : CER/WER/MER aujourd'hui) — **jamais** par les métriques que le
design *dessine* mais que le moteur ne produit pas encore (note d'archi S4.b :
pas de rapport en avance sur sa donnée). Les sections plus riches arrivent au fil
des métriques (T7).
"""

from __future__ import annotations

from xerocr.evaluation.result import RunResult
from xerocr.reports.html import escape
from xerocr.reports.section import Html, SectionContext
from xerocr.reports.sections._tables import bar_cell, col_max, ordered_unique


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
        views = ordered_unique(p.view for p in result.pipelines)
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


def _table_for_view(result: RunResult, view_name: str) -> str:
    pipelines = [p for p in result.pipelines if p.view == view_name]
    metrics = tuple(score.metric for score in pipelines[0].aggregate)
    header = "".join(f'<th class="num-cell">{escape(m)}</th>' for m in metrics)
    rows = [p.aggregate for p in pipelines]
    maxes = [col_max(rows, i) for i in range(len(metrics))]
    body_rows: list[str] = []
    for pipeline in pipelines:
        cells = "".join(
            bar_cell(score, maxes[i]) for i, score in enumerate(pipeline.aggregate)
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
