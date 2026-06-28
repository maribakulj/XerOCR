"""Section by-engine : **comparaison** des moteurs sur la vue primaire +
**dispersion** du taux d'erreur par-document. Couche 7.

Distinct de l'overview (tables descriptives, une par vue) : ici **une** table de
toutes les familles de métriques, **ordonnée** par CER croissant (un tri, pas un
verdict — aucun rang ordinal n'est attribué), plus l'**étendue** (min · médiane ·
max) du CER sur les documents, c.-à-d. la **fiabilité** que l'agrégat masque (et
que ni l'overview ni le par-document ne donnent). On expose les chiffres ;
l'utilisateur interprète (aucun gagnant déclaré — cf. ``key_measures`` §6/§12).
"""

from __future__ import annotations

from statistics import median

from cinoc.evaluation.result import PipelineResult, RunDocumentResult, RunResult
from cinoc.reports._numbers import localize_decimal
from cinoc.reports.engine_badges import engine_cell, engine_order
from cinoc.reports.html import escape, localized, view_label
from cinoc.reports.section import Html, SectionContext
from cinoc.reports.sections._tables import (
    bar_cell,
    bar_legend,
    col_max,
    group_header_row,
    metric_th,
    nonempty_metric_indices,
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
    """Comparaison des moteurs (vue primaire) + dispersion par-document du CER."""

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
        sort_metric = "cer" if "cer" in metrics else metrics[0]
        sort_idx = metrics.index(sort_metric)

        def _key(p: PipelineResult) -> tuple[bool, float, str]:
            value = p.aggregate[sort_idx].value
            return (value is None, value if value is not None else 0.0, p.pipeline)

        ordered = sorted(rows, key=_key)
        # Badge moteur (lettre + accent) = identité STABLE, indépendante du rang :
        # ordre canonique = première apparition dans le run (partagé entre sections).
        order = engine_order(p.pipeline for p in result.pipelines)
        keep = nonempty_metric_indices([p.aggregate for p in rows])  # masque tout-« — »
        maxes = [col_max([p.aggregate for p in rows], i) for i in keep]
        profil_title = localized(ctx.lang, "Profil", "Profile")
        body: list[str] = []
        # Lignes ordonnées par CER croissant (un **tri** lisible, pas un rang
        # ordinal attribué : aucune colonne « # », aucun gagnant désigné).
        for pipeline in ordered:
            cells = "".join(
                bar_cell(
                    pipeline.aggregate[i], maxes[j], lang=ctx.lang, sortable=True
                )
                for j, i in enumerate(keep)
            )
            vals = _per_doc_values(
                result.documents, pipeline.pipeline, view, sort_metric
            )
            disp = (
                localize_decimal(
                    f"{min(vals):.3f} · {median(vals):.3f} · {max(vals):.3f}",
                    ctx.lang,
                )
                if vals
                else "—"
            )
            idx = order.get(pipeline.pipeline, 0)
            badge = engine_cell(pipeline.pipeline, idx)
            # Le **nom du moteur** est le lien vers son profil drill-in (#engine-N) :
            # cliquer le moteur ouvre son analyse détaillée (≠ une petite flèche).
            body.append(
                f'<tr><td class="eng-cell"><a href="#engine-{idx}" '
                f'title="{profil_title}">{badge}</a></td>{cells}'
                f'<td class="disp">{disp}</td></tr>'
            )
        display_metrics = [metrics[i] for i in keep]
        header = "".join(
            metric_th(m, ctx.lang, sortable=True) for m in display_metrics
        )
        # Suffixe de vue seulement si plusieurs vues à distinguer (sinon bruit).
        multi = len(ordered_unique(p.view for p in result.pipelines)) > 1
        vlbl = escape(view_label(view, ctx.lang))
        heading = localized(
            ctx.lang,
            f"Comparaison des moteurs{f' (vue : {vlbl})' if multi else ''}",
            f"Engine comparison{f' (view: {vlbl})' if multi else ''}",
        )
        prose = localized(
            ctx.lang,
            f'<p class="muted">Ordonné par {escape(sort_metric)} ↑ (un tri, pas un '
            f"rang attribué) · dispersion = {escape(sort_metric)} min · médiane · "
            "max par document. Cliquer un en-tête de métrique pour réordonner ; "
            "survoler pour la définition. Aucun gagnant n'est déclaré.</p>\n",
            f'<p class="muted">Ordered by {escape(sort_metric)} ↑ (a sort, not an '
            f"assigned rank) · dispersion = {escape(sort_metric)} min · median · "
            "max per document. Click a metric header to reorder; hover for the "
            "definition. No winner is declared.</p>\n",
        )
        th_engine = localized(ctx.lang, "Moteur", "Engine")
        th_dispersion = localized(ctx.lang, "dispersion", "dispersion")
        return Html(
            f"<h2>{heading}</h2>\n"
            + prose
            + '<div class="table-scroll"><table class="data sortable">\n'
            "<thead>"
            + group_header_row(display_metrics, ctx.lang, lead=1, trail=1)
            + f"<tr><th>{th_engine}</th>{header}"
            f'<th class="num-cell">{th_dispersion}</th></tr></thead>\n'
            f"<tbody>{''.join(body)}</tbody>\n</table></div>\n"
            + bar_legend(ctx.lang)
        )


__all__ = ["EngineSection"]
