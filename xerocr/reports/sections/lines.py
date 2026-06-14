"""Section distribution par ligne : rend le payload ``lines`` au design.

Lecture seule du payload (aucun recalcul) : par pipeline, la distribution du
CER par ligne — percentiles, Gini, taux de lignes catastrophiques — puis la
heatmap positionnelle (où, dans les documents, les erreurs se concentrent).
Pédagogie en prose, aucun scalaire de classement (pas de glossaire).
"""

from __future__ import annotations

from collections.abc import Mapping

from xerocr.evaluation.analysis import LinesPayload, PipelineLines
from xerocr.evaluation.result import RunResult
from xerocr.reports.engine_badges import engine_cell, engine_order
from xerocr.reports.html import escape, localized
from xerocr.reports.section import Html, SectionContext


def _distribution_row(row: PipelineLines, order: Mapping[str, int]) -> str:
    badge = engine_cell(row.pipeline, order.get(row.pipeline, 0))
    p = row.percentiles
    catastrophic = " · ".join(
        f"≥{item.threshold:.2f} : {item.rate:.1%}" for item in row.catastrophic
    )
    return (
        f'<tr><td class="eng-cell">{badge}</td>'
        f'<td class="disp">{row.line_count}</td>'
        f'<td class="disp">{row.mean_cer:.1%}</td>'
        f'<td class="disp">{p.p50:.1%}</td>'
        f'<td class="disp">{p.p75:.1%}</td>'
        f'<td class="disp">{p.p90:.1%}</td>'
        f'<td class="disp">{p.p95:.1%}</td>'
        f'<td class="disp">{p.p99:.1%}</td>'
        f'<td class="disp">{row.gini:.3f}</td>'
        f'<td class="disp">{catastrophic}</td></tr>'
    )


def _heatmap_row(row: PipelineLines, order: Mapping[str, int]) -> str:
    badge = engine_cell(row.pipeline, order.get(row.pipeline, 0))
    cells = "".join(
        f'<td class="disp">{value:.1%}</td>'
        if value is not None
        else '<td class="disp">—</td>'
        for value in row.heatmap
    )
    return f'<tr><td class="eng-cell">{badge}</td>{cells}</tr>'


def _block(
    view: str, payload: LinesPayload, order: Mapping[str, int], lang: str
) -> str:
    rows = "".join(_distribution_row(row, order) for row in payload.pipelines)
    heatmap_rows = "".join(_heatmap_row(row, order) for row in payload.pipelines)
    bin_headers = "".join(
        f'<th class="num-cell">{i + 1}/{payload.heatmap_bins}</th>'
        for i in range(payload.heatmap_bins)
    )
    dist_head = localized(
        lang,
        f"{escape(view)} — distribution du CER par ligne",
        f"{escape(view)} — per-line CER distribution",
    )
    dist_prose = localized(
        lang,
        '<p class="muted">Toutes les lignes GT du corpus, appariées aux lignes '
        "produites par alignement (une ligne insérée/supprimée ne décale pas "
        "les suivantes ; ligne perdue = CER 1,0). Le Gini lit la "
        "concentration : 0 = erreurs uniformes (correction rapide partout), "
        "1 = concentrées sur quelques lignes détruites (re-saisie locale). "
        "« Catastrophiques » = part des lignes au CER ≥ seuil.</p>\n",
        '<p class="muted">All GT lines of the corpus, matched to the lines '
        "produced by alignment (an inserted/deleted line does not shift "
        "the following ones; lost line = CER 1.0). Gini reads the "
        "concentration: 0 = uniform errors (fast correction everywhere), "
        "1 = concentrated on a few destroyed lines (local re-keying). "
        '"Catastrophic" = share of lines with CER ≥ threshold.</p>\n',
    )
    th_pipeline = localized(lang, "Pipeline", "Pipeline")
    th_lines = localized(lang, "lignes", "lines")
    th_mean_cer = localized(lang, "CER moyen", "mean CER")
    th_catastrophic = localized(lang, "catastrophiques", "catastrophic")
    heat_head = localized(
        lang,
        f"{escape(view)} — heatmap positionnelle (début → fin de document)",
        f"{escape(view)} — positional heatmap (document start → end)",
    )
    heat_prose = localized(
        lang,
        '<p class="muted">CER moyen par tranche de position relative dans le '
        "document — un moteur qui décroche en bas de page (fatigue de "
        "colonne, marges) se voit ici ; « — » = aucune ligne dans la "
        "tranche.</p>\n",
        '<p class="muted">Mean CER per slice of relative position within the '
        "document — an engine that drops off at the bottom of the page (column "
        'fatigue, margins) shows up here; "—" = no line in the '
        "slice.</p>\n",
    )
    return (
        f"<h3>{dist_head}</h3>\n"
        f"{dist_prose}"
        f'<table class="data">\n<thead><tr><th>{th_pipeline}</th>'
        f'<th class="num-cell">{th_lines}</th>'
        f'<th class="num-cell">{th_mean_cer}</th>'
        '<th class="num-cell">p50</th><th class="num-cell">p75</th>'
        '<th class="num-cell">p90</th><th class="num-cell">p95</th>'
        '<th class="num-cell">p99</th><th class="num-cell">Gini</th>'
        f"<th>{th_catastrophic}</th></tr></thead>\n"
        f"<tbody>{rows}</tbody>\n</table>\n"
        f"<h3>{heat_head}</h3>\n"
        f"{heat_prose}"
        f'<table class="data">\n<thead><tr><th>{th_pipeline}</th>'
        f"{bin_headers}</tr></thead>\n"
        f"<tbody>{heatmap_rows}</tbody>\n</table>\n"
    )


class LinesSection:
    """Distribution du CER par ligne, par pipeline (lecture seule)."""

    name = "lines"
    requires: tuple[str, ...] = ()

    def render(self, result: RunResult, ctx: SectionContext) -> Html | None:
        order = engine_order(p.pipeline for p in result.pipelines)
        blocks = [
            _block(analysis.view, analysis.payload, order, ctx.lang)
            for analysis in result.analyses
            if isinstance(analysis.payload, LinesPayload)
        ]
        if not blocks:
            return None
        title = localized(
            ctx.lang,
            "Distribution des erreurs par ligne",
            "Per-line error distribution",
        )
        return Html(f"<h2>{title}</h2>\n" + "".join(blocks))


__all__ = ["LinesSection"]
