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
from xerocr.reports.html import escape, localized
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


def _block(
    view: str, payload: NerPayload, order: Mapping[str, int], lang: str
) -> str:
    global_rows = "".join(_global_row(row, order) for row in payload.pipelines)
    category_rows = "".join(_category_rows(row, order) for row in payload.pipelines)
    samples_rows = "".join(_samples_rows(row, order) for row in payload.pipelines)
    th_pipeline = localized(lang, "Pipeline", "Pipeline")
    th_precision = localized(lang, "précision", "precision")
    th_recall = localized(lang, "rappel", "recall")
    global_head = localized(
        lang,
        f"{escape(view)} — entités nommées (IoU ≥ {payload.iou_threshold:.2f})",
        f"{escape(view)} — named entities (IoU ≥ {payload.iou_threshold:.2f})",
    )
    global_prose = localized(
        lang,
        '<p class="muted">Part des entités de la GT retrouvées dans la sortie, '
        "spans alignés en coordonnées GT (un décalage d'OCR amont ne pénalise "
        "pas une entité bien transcrite). La mesure est <strong>conjointe</strong> "
        "— elle reflète l'OCR <em>et</em> l'extracteur NER. TP/FP/FN = vrais "
        "positifs / hallucinés / manqués.</p>\n",
        '<p class="muted">Share of GT entities found in the output, '
        "spans aligned in GT coordinates (an upstream OCR shift does not penalize "
        "a well-transcribed entity). The measure is <strong>joint</strong> "
        "— it reflects the OCR <em>and</em> the NER extractor. TP/FP/FN = true "
        "positives / hallucinated / missed.</p>\n",
    )
    th_gt_entities = localized(lang, "entités GT", "GT entities")
    blocks = (
        f"<h3>{global_head}</h3>\n"
        f"{global_prose}"
        f'<table class="data">\n<thead><tr><th>{th_pipeline}</th>'
        f'<th class="num-cell">{th_gt_entities}</th>'
        f'<th class="num-cell">{th_precision}</th>'
        f'<th class="num-cell">{th_recall}</th><th class="num-cell">F1</th>'
        '<th class="num-cell">TP/FP/FN</th></tr></thead>\n'
        f"<tbody>{global_rows}</tbody>\n</table>\n"
    )
    if category_rows:
        cat_head = localized(
            lang,
            f"{escape(view)} — F1 par catégorie",
            f"{escape(view)} — F1 per category",
        )
        th_category = localized(lang, "catégorie", "category")
        th_support = localized(lang, "support", "support")
        blocks += (
            f"<h3>{cat_head}</h3>\n"
            f'<table class="data">\n<thead><tr><th>{th_pipeline}</th>'
            f"<th>{th_category}</th>"
            f'<th class="num-cell">{th_support}</th>'
            f'<th class="num-cell">{th_precision}</th>'
            f'<th class="num-cell">{th_recall}</th><th class="num-cell">F1</th>'
            "</tr></thead>\n"
            f"<tbody>{category_rows}</tbody>\n</table>\n"
        )
    samples_head = localized(
        lang,
        f"{escape(view)} — entités manquées &amp; hallucinées (échantillon)",
        f"{escape(view)} — missed &amp; hallucinated entities (sample)",
    )
    th_missed = localized(lang, "manquées", "missed")
    th_hallucinated = localized(lang, "hallucinées", "hallucinated")
    blocks += (
        f"<h3>{samples_head}</h3>\n"
        f'<table class="data">\n<thead><tr><th>{th_pipeline}</th>'
        f"<th>{th_missed}</th>"
        f"<th>{th_hallucinated}</th></tr></thead>\n"
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
            _block(analysis.view, analysis.payload, order, ctx.lang)
            for analysis in result.analyses
            if isinstance(analysis.payload, NerPayload)
        ]
        if not blocks:
            return None
        title = localized(ctx.lang, "Entités nommées", "Named entities")
        return Html(f"<h2>{title}</h2>\n" + "".join(blocks))


__all__ = ["NerSection"]
