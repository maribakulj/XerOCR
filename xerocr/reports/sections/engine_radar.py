"""Section radar : profil multi-métrique par moteur, superposé (couche 7).

Un seul graphique « toile d'araignée » qui superpose tous les moteurs sur des
axes normalisés « plus loin = meilleur » ([0,1]) — la **forme** de chaque
polygone révèle ses forces/faiblesses d'un coup d'œil. Pure présentation : lit
les scores d'agrégat du ``RunResult`` (aucun recalcul), rendu SVG serveur
déterministe (≠ Chart.js), zéro JS.
"""

from __future__ import annotations

from xerocr.evaluation.result import RunResult
from xerocr.reports.engine_badges import engine_accent, engine_letter, engine_order
from xerocr.reports.html import escape, localized
from xerocr.reports.section import Html, SectionContext
from xerocr.reports.sections._tables import ordered_unique
from xerocr.reports.svg import radar_chart

#: Axes du radar : (clé métrique, inverser ?, libellé fr, libellé en). Toutes les
#: valeurs sont ramenées à « plus haut = meilleur » dans [0,1] (les métriques
#: d'erreur — hallucination — sont inversées : 1 − valeur).
_AXES: tuple[tuple[str, bool, str, str], ...] = (
    ("char_accuracy", False, "Caract.", "Char."),
    ("word_accuracy", False, "Mot", "Word"),
    ("fca", False, "Fidél.", "Fidel."),
    ("bow_f1", False, "F1", "F1"),
    ("searchability", False, "Rech.", "Search"),
    ("hallucination", True, "¬Halluc", "¬Halluc"),
)


class EngineRadarSection:
    """Radar multi-métrique superposant tous les moteurs (carte autonome)."""

    name = "engine_radar"
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
        # Axes retenus : ceux présents pour **tous** les moteurs affichés (sinon le
        # polygone n'est pas comparable). Radar utile à partir de 3 axes.
        axes = [
            ax for ax in _AXES if all(ax[0] in scores[p.pipeline] for p in pipes)
        ]
        if len(axes) < 3:
            return None
        labels = [ax[2] if ctx.lang != "en" else ax[3] for ax in axes]
        series: list[tuple[str, list[float]]] = []
        accents: list[str] = []
        for p in pipes:
            values = []
            for key, invert, _fr, _en in axes:
                v = scores[p.pipeline][key]
                values.append(1.0 - v if invert else v)
            series.append((p.pipeline, values))
            accents.append(engine_accent(order[p.pipeline]))
        svg = radar_chart(labels, series, accents=accents)
        if not svg:
            return None
        legend = " · ".join(
            f'<span class="eng-badge" style="--badge:{engine_accent(i)}">'
            f"{engine_letter(i)}</span> {escape(p.pipeline)}"
            for p in pipes
            for i in (order[p.pipeline],)
        )
        title = localized(ctx.lang, "Profil radar", "Radar profile")
        intro = localized(
            ctx.lang,
            "Profil multi-métrique par moteur — chaque axe normalisé « plus loin "
            "= meilleur » ([0,1]). Polygones superposés : la forme révèle les "
            "forces et faiblesses de chaque moteur.",
            "Multi-metric profile per engine — each axis normalised 'further = "
            "better' ([0,1]). Overlaid polygons: the shape reveals each engine's "
            "strengths and weaknesses.",
        )
        return Html(
            f"<h2>{title}</h2>\n"
            f'<p class="muted">{intro}</p>\n'
            f'<div class="radar-wrap">{svg}</div>\n'
            f'<p class="muted radar-legend">{legend}</p>\n'
        )


__all__ = ["EngineRadarSection"]
