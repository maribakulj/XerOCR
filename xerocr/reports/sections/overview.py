"""Section overview : tableau pipelines × métriques (par vue) + en-tête corpus."""

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


class OverviewSection:
    """Vue d'ensemble : une ligne par pipeline, une colonne par métrique."""

    name = "overview"
    requires: tuple[str, ...] = ()  # générique : affiche les métriques présentes

    def render(self, result: RunResult, ctx: SectionContext) -> Html | None:
        if not result.pipelines:
            return None
        parts: list[str] = [
            "<h2>Vue d'ensemble</h2>",
            (
                f'<p class="muted">Corpus : {escape(result.manifest.corpus_name)} '
                f"— {result.manifest.n_documents} document(s)</p>"
            ),
        ]
        for view_name in _views_in_order(result.pipelines):
            parts.append(_table_for_view(result, view_name))
        return Html("\n".join(parts) + "\n")


def _table_for_view(result: RunResult, view_name: str) -> str:
    pipelines = [p for p in result.pipelines if p.view == view_name]
    metrics = tuple(score.metric for score in pipelines[0].aggregate)
    header = "".join(f"<th>{escape(m)}</th>" for m in metrics)
    body_rows: list[str] = []
    for pipeline in pipelines:
        cells = "".join(
            f'<td class="num">{_format_value(score)}</td>'
            for score in pipeline.aggregate
        )
        body_rows.append(f"<tr><td>{escape(pipeline.pipeline)}</td>{cells}</tr>")
    return (
        f"<h2>Vue : {escape(view_name)}</h2>\n"
        f"<table>\n<thead><tr><th>Pipeline</th>{header}</tr></thead>\n"
        f"<tbody>{''.join(body_rows)}</tbody>\n</table>"
    )


__all__ = ["OverviewSection"]
