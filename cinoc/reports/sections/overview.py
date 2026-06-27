"""Section overview : bande de **readouts** (portée du corpus) + une table par
vue, pipelines × métriques, avec **data-bars** proportionnelles. Couche 7.

Le contenu reste piloté par les **vraies** métriques de ``RunResult`` (ce que le
moteur calcule : CER/WER/MER aujourd'hui) — **jamais** par les métriques que le
design *dessine* mais que le moteur ne produit pas encore (note d'archi :
pas de rapport en avance sur sa donnée). Les sections plus riches arrivent au fil
des métriques.
"""

from __future__ import annotations

from cinoc.evaluation.result import RunResult
from cinoc.reports.engine_badges import engine_cell, engine_order
from cinoc.reports.html import escape, localized, view_label
from cinoc.reports.section import Html, SectionContext
from cinoc.reports.sections._tables import (
    bar_cell,
    bar_legend,
    col_max,
    group_header_row,
    metric_short_label,
    nonempty_metric_indices,
    ordered_unique,
)


class OverviewSection:
    """Métriques par vue (data-bars). La **portée** (docs/moteurs) vit dans le
    héros de la vue (rendu par le renderer), plus dans une bande de readouts ici."""

    name = "overview"
    requires: tuple[str, ...] = ()  # générique : affiche les métriques présentes

    def render(self, result: RunResult, ctx: SectionContext) -> Html | None:
        if not result.pipelines:
            return None
        views = ordered_unique(p.view for p in result.pipelines)
        corpus = localized(ctx.lang, "Corpus", "Corpus")
        parts: list[str] = [
            f"<h2>{localized(ctx.lang, 'Métriques par vue', 'Metrics per view')}</h2>",
            f'<p class="muted">{corpus} : '
            f"{escape(result.manifest.corpus_name)}</p>",
        ]
        multi = len(views) > 1
        for view_name in views:
            parts.append(_table_for_view(result, view_name, ctx.lang, multi=multi))
        return Html("\n".join(parts) + "\n")


def _table_for_view(
    result: RunResult, view_name: str, lang: str, *, multi: bool
) -> str:
    pipelines = [p for p in result.pipelines if p.view == view_name]
    order = engine_order(p.pipeline for p in result.pipelines)
    rows = [p.aggregate for p in pipelines]
    keep = nonempty_metric_indices(rows)  # masque les colonnes tout-« — »
    all_metrics = tuple(score.metric for score in pipelines[0].aggregate)
    metrics = [all_metrics[i] for i in keep]
    header = "".join(
        f'<th class="num-cell" title="{escape(m)}">'
        f"{escape(metric_short_label(m))}</th>"
        for m in metrics
    )
    maxes = [col_max(rows, i) for i in keep]
    body_rows: list[str] = []
    for pipeline in pipelines:
        cells = "".join(
            bar_cell(pipeline.aggregate[i], maxes[j]) for j, i in enumerate(keep)
        )
        badge = engine_cell(pipeline.pipeline, order.get(pipeline.pipeline, 0))
        body_rows.append(f'<tr><td class="eng-cell">{badge}</td>{cells}</tr>')
    # Libellé de vue affiché **seulement** s'il y a plusieurs vues à distinguer
    # (sinon « Métriques par vue » + la ligne corpus suffisent — pas de ressassage).
    head = ""
    if multi:
        view_caption = localized(lang, "Vue", "View")
        head = f"<h2>{view_caption} : {escape(view_label(view_name, lang))}</h2>\n"
    return (
        f"{head}"
        '<div class="table-scroll">'
        f'<table class="data">\n<thead>{group_header_row(metrics, lang, lead=1)}'
        f"<tr><th>Pipeline</th>{header}</tr></thead>\n"
        f"<tbody>{''.join(body_rows)}</tbody>\n</table></div>\n"
        f"{bar_legend(lang)}"
    )


__all__ = ["OverviewSection"]
