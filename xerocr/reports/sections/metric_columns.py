"""Section colonnes métriques : comparatif moteur en colonnes groupées (couche 7).

Pour chaque métrique d'exactitude (toutes naturellement « plus haut = meilleur »
dans [0,1]), une colonne par moteur — la lecture **exacte des hauteurs** complète
le radar (qui donne la forme). Pure présentation : lit les scores d'agrégat du
``RunResult`` (aucun recalcul), rendu SVG serveur déterministe, zéro JS.
"""

from __future__ import annotations

from xerocr.evaluation.result import RunResult
from xerocr.reports.engine_badges import engine_accent, engine_letter, engine_order
from xerocr.reports.html import escape, localized
from xerocr.reports.section import Html, SectionContext
from xerocr.reports.sections._tables import ordered_unique
from xerocr.reports.svg import grouped_columns

#: Métriques affichées (clé, libellé fr, libellé en) — toutes « plus haut =
#: meilleur » dans [0,1], donc tracées telles quelles (pas d'inversion).
_METRICS: tuple[tuple[str, str, str], ...] = (
    ("char_accuracy", "Caract.", "Char."),
    ("word_accuracy", "Mot", "Word"),
    ("bow_f1", "F1", "F1"),
    ("searchability", "Rech.", "Search"),
)


class MetricColumnsSection:
    """Colonnes groupées : exactitude par métrique × moteur (carte autonome)."""

    name = "metric_columns"
    requires: tuple[str, ...] = ()

    def render(self, result: RunResult, ctx: SectionContext) -> Html | None:
        if not result.pipelines:
            return None
        view = ordered_unique(p.view for p in result.pipelines)[0]
        order = engine_order(p.pipeline for p in result.pipelines)
        pipes = sorted(
            (p for p in result.pipelines if p.view == view),
            key=lambda p: order[p.pipeline],
        )
        if not pipes:
            return None
        scores = {
            p.pipeline: {s.metric: s.value for s in p.aggregate if s.value is not None}
            for p in pipes
        }
        # Métriques retenues : présentes pour **tous** les moteurs (colonnes
        # comparables). Au moins une requise.
        metrics = [
            m for m in _METRICS if all(m[0] in scores[p.pipeline] for p in pipes)
        ]
        if not metrics:
            return None
        groups = [m[1] if ctx.lang != "en" else m[2] for m in metrics]
        series: list[tuple[str, list[float]]] = []
        accents: list[str] = []
        for p in pipes:
            series.append((p.pipeline, [scores[p.pipeline][m[0]] for m in metrics]))
            accents.append(engine_accent(order[p.pipeline]))
        svg = grouped_columns(groups, series, accents=accents)
        if not svg:
            return None
        legend = " · ".join(
            f'<span class="eng-badge" style="--badge:{engine_accent(i)}">'
            f"{engine_letter(i)}</span> {escape(p.pipeline)}"
            for p in pipes
            for i in (order[p.pipeline],)
        )
        title = localized(ctx.lang, "Colonnes métriques", "Metric columns")
        intro = localized(
            ctx.lang,
            "Exactitude par métrique (plus haut = meilleur), une colonne par "
            "moteur — la hauteur exacte se lit d'un coup d'œil.",
            "Accuracy per metric (higher = better), one column per engine — exact "
            "heights read at a glance.",
        )
        return Html(
            f"<h2>{title}</h2>\n"
            f'<p class="muted">{intro}</p>\n'
            f'<div class="col-wrap">{svg}</div>\n'
            f'<p class="muted col-legend">{legend}</p>\n'
        )


__all__ = ["MetricColumnsSection"]
