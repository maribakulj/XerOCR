"""Section entités nommées : précision/rappel/F1 par pipeline (couche 7).

Lecture seule du payload ``ner`` : F1 global + détail par catégorie, échantillon
des entités manquées et hallucinées. La prose documente la limite — la métrique
mesure **conjointement** la qualité de l'OCR et celle de l'extracteur NER.
"""

from __future__ import annotations

from collections.abc import Mapping

from xerocr.evaluation.analysis import EntityMention, NerPayload, PipelineNer
from xerocr.evaluation.result import RunResult
from xerocr.reports.engine_badges import engine_cell, engine_order
from xerocr.reports.html import escape
from xerocr.reports.section import Html, SectionContext


def _mentions(mentions: tuple[EntityMention, ...]) -> str:
    if not mentions:
        return "—"
    labels = ", ".join(
        f"{escape(m.text)} ({escape(m.label)})" if m.text else escape(m.label)
        for m in mentions
    )
    return f'<span class="muted">{labels}</span>'


def _global_row(row: PipelineNer, order: Mapping[str, int]) -> str:
    badge = engine_cell(row.pipeline, order.get(row.pipeline, 0))
    return (
        f'<tr><td class="eng-cell">{badge}</td>'
        f'<td class="disp">{row.n_reference}</td>'
        f'<td class="disp">{row.precision:.1%}</td>'
        f'<td class="disp">{row.recall:.1%}</td>'
        f'<td class="disp">{row.f1:.1%}</td>'
        f'<td class="disp">{row.true_positives}/{row.false_positives}'
        f"/{row.false_negatives}</td></tr>"
    )


def _category_rows(row: PipelineNer, order: Mapping[str, int]) -> str:
    rows: list[str] = []
    for cat in row.per_category:
        badge = engine_cell(row.pipeline, order.get(row.pipeline, 0))
        rows.append(
            f'<tr><td class="eng-cell">{badge}</td>'
            f'<td class="eng-cell">{escape(cat.label)}</td>'
            f'<td class="disp">{cat.support}</td>'
            f'<td class="disp">{cat.precision:.1%}</td>'
            f'<td class="disp">{cat.recall:.1%}</td>'
            f'<td class="disp">{cat.f1:.1%}</td></tr>'
        )
    return "".join(rows)


def _samples_rows(row: PipelineNer, order: Mapping[str, int]) -> str:
    badge = engine_cell(row.pipeline, order.get(row.pipeline, 0))
    return (
        f'<tr><td class="eng-cell">{badge}</td>'
        f"<td>{_mentions(row.missed)}</td>"
        f"<td>{_mentions(row.hallucinated)}</td></tr>"
    )


def _block(view: str, payload: NerPayload, order: Mapping[str, int]) -> str:
    global_rows = "".join(_global_row(row, order) for row in payload.pipelines)
    category_rows = "".join(_category_rows(row, order) for row in payload.pipelines)
    samples_rows = "".join(_samples_rows(row, order) for row in payload.pipelines)
    blocks = (
        f"<h3>{escape(view)} — entités nommées "
        f"(IoU ≥ {payload.iou_threshold:.2f})</h3>\n"
        '<p class="muted">Part des entités de la GT retrouvées dans la sortie, '
        "spans alignés en coordonnées GT (un décalage d'OCR amont ne pénalise "
        "pas une entité bien transcrite). La mesure est <strong>conjointe</strong> "
        "— elle reflète l'OCR <em>et</em> l'extracteur NER. TP/FP/FN = vrais "
        "positifs / hallucinés / manqués.</p>\n"
        '<table class="data">\n<thead><tr><th>Pipeline</th>'
        '<th class="num-cell">entités GT</th><th class="num-cell">précision</th>'
        '<th class="num-cell">rappel</th><th class="num-cell">F1</th>'
        '<th class="num-cell">TP/FP/FN</th></tr></thead>\n'
        f"<tbody>{global_rows}</tbody>\n</table>\n"
    )
    if category_rows:
        blocks += (
            f"<h3>{escape(view)} — F1 par catégorie</h3>\n"
            '<table class="data">\n<thead><tr><th>Pipeline</th><th>catégorie</th>'
            '<th class="num-cell">support</th><th class="num-cell">précision</th>'
            '<th class="num-cell">rappel</th><th class="num-cell">F1</th>'
            "</tr></thead>\n"
            f"<tbody>{category_rows}</tbody>\n</table>\n"
        )
    blocks += (
        f"<h3>{escape(view)} — entités manquées &amp; hallucinées "
        "(échantillon)</h3>\n"
        '<table class="data">\n<thead><tr><th>Pipeline</th><th>manquées</th>'
        "<th>hallucinées</th></tr></thead>\n"
        f"<tbody>{samples_rows}</tbody>\n</table>\n"
    )
    return blocks


class NerSection:
    """Précision sur entités nommées, par pipeline (lecture seule)."""

    name = "ner"
    requires: tuple[str, ...] = ()

    def render(self, result: RunResult, ctx: SectionContext) -> Html | None:
        order = engine_order(p.pipeline for p in result.pipelines)
        blocks = [
            _block(analysis.view, analysis.payload, order)
            for analysis in result.analyses
            if isinstance(analysis.payload, NerPayload)
        ]
        if not blocks:
            return None
        return Html("<h2>Entités nommées</h2>\n" + "".join(blocks))


__all__ = ["NerSection"]
