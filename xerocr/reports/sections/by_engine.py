"""Section by-engine : **classement** des moteurs sur la vue primaire + **dispersion**
du taux d'erreur par-document. Couche 7.

Distinct de l'overview (tables descriptives, une par vue) : ici **une** table
**triée** — le verdict « quel moteur gagne » — plus l'**étendue** (min · médiane ·
max) du CER sur les documents, c.-à-d. la **fiabilité** que l'agrégat masque (et
que ni l'overview ni le par-document ne donnent). Métriques **réelles** seulement
(cer/wer/mer) ; un classement chiffré n'est pas de la prose (narratif supprimé).
"""

from __future__ import annotations

from statistics import median

from xerocr.evaluation.result import PipelineResult, RunDocumentResult, RunResult
from xerocr.reports.engine_badges import engine_cell, engine_order
from xerocr.reports.html import escape
from xerocr.reports.section import Html, SectionContext
from xerocr.reports.sections._tables import (
    bar_cell,
    col_max,
    metric_th,
    ordered_unique,
)


def _per_doc_values(
    documents: tuple[RunDocumentResult, ...], pipeline: str, view: str, metric: str
) -> list[float]:
    """Valeurs par-document (non ``None``) d'une métrique pour un moteur/vue."""
    out: list[float] = []
    for doc in documents:
        if doc.pipeline == pipeline and doc.view == view:
            for score in doc.scores:
                if score.metric == metric and score.value is not None:
                    out.append(score.value)
    return out


class EngineSection:
    """Classement des moteurs (vue primaire) + dispersion par-document du CER."""

    name = "by_engine"
    requires: tuple[str, ...] = ()

    def render(self, result: RunResult, ctx: SectionContext) -> Html | None:
        if not result.pipelines:
            return None
        view = ordered_unique(p.view for p in result.pipelines)[0]
        rows = [p for p in result.pipelines if p.view == view]
        metrics = tuple(s.metric for s in rows[0].aggregate)
        if not metrics:
            return None
        rank = "cer" if "cer" in metrics else metrics[0]
        rank_idx = metrics.index(rank)

        def _key(p: PipelineResult) -> tuple[bool, float, str]:
            value = p.aggregate[rank_idx].value
            return (value is None, value if value is not None else 0.0, p.pipeline)

        ordered = sorted(rows, key=_key)
        # Badge moteur (lettre + accent) = identité STABLE, indépendante du rang :
        # ordre canonique = première apparition dans le run (partagé entre sections).
        order = engine_order(p.pipeline for p in result.pipelines)
        maxes = [col_max([p.aggregate for p in rows], i) for i in range(len(metrics))]
        body: list[str] = []
        for position, pipeline in enumerate(ordered, start=1):
            cells = "".join(
                bar_cell(s, maxes[i], sortable=True)
                for i, s in enumerate(pipeline.aggregate)
            )
            vals = _per_doc_values(result.documents, pipeline.pipeline, view, rank)
            disp = (
                f"{min(vals):.3f} · {median(vals):.3f} · {max(vals):.3f}"
                if vals
                else "—"
            )
            badge = engine_cell(pipeline.pipeline, order.get(pipeline.pipeline, 0))
            body.append(
                f'<tr><td class="rank">{position}</td>'
                f'<td class="eng-cell">{badge}</td>{cells}'
                f'<td class="disp">{disp}</td></tr>'
            )
        header = "".join(metric_th(m, ctx.lang, sortable=True) for m in metrics)
        return Html(
            f"<h2>Classement (vue : {escape(view)})</h2>\n"
            f'<p class="muted">Trié par {escape(rank)} ↑ · dispersion = '
            f"{escape(rank)} min · médiane · max par document. "
            "Cliquer un en-tête de métrique pour trier ; survoler pour la "
            "définition.</p>\n"
            f'<table class="data sortable">\n'
            f'<thead><tr><th>#</th><th>Moteur</th>{header}'
            f'<th class="num-cell">dispersion</th></tr></thead>\n'
            f"<tbody>{''.join(body)}</tbody>\n</table>\n"
        )


__all__ = ["EngineSection"]
