"""Section qualité × erreur : nuage de bulles document (couche 7).

Une bulle par (document, moteur) : **X** = score de qualité de l'image, **Y** =
CER du moteur sur ce document, **taille** ∝ nombre de caractères (volume), couleur
= moteur. Révèle si les numérisations dégradées (gauche) tirent le CER vers le
haut, et quels gros documents sont durs. Pure présentation : lit le payload
``image_quality`` (par document) + les CER par document du ``RunResult`` (aucun
recalcul), rendu SVG serveur déterministe, zéro JS.
"""

from __future__ import annotations

from xerocr.evaluation.analysis import ImageQualityPayload
from xerocr.evaluation.result import RunResult
from xerocr.reports.engine_badges import engine_accent, engine_letter, engine_order
from xerocr.reports.html import escape, localized
from xerocr.reports.section import Html, SectionContext
from xerocr.reports.sections._tables import ordered_unique
from xerocr.reports.svg import bubble_chart

_METRIC = "cer"


def _quality_by_doc(result: RunResult, view: str) -> dict[str, float]:
    """``{document_id: quality_score}`` du payload image_quality (corpus), ou {}."""
    for analysis in result.analyses:
        payload = analysis.payload
        if analysis.view == view and isinstance(payload, ImageQualityPayload):
            return {d.document_id: d.quality_score for d in payload.documents}
    # le payload image_quality est scope corpus : sa vue peut différer — on prend
    # le premier rencontré quelle que soit la vue.
    for analysis in result.analyses:
        if isinstance(analysis.payload, ImageQualityPayload):
            return {d.document_id: d.quality_score for d in analysis.payload.documents}
    return {}


class QualityErrorSection:
    """Nuage de bulles qualité d'image × CER × volume, par document et moteur."""

    name = "quality_error"
    requires: tuple[str, ...] = ()

    def render(self, result: RunResult, ctx: SectionContext) -> Html | None:
        if not result.pipelines:
            return None
        view = ordered_unique(p.view for p in result.pipelines)[0]
        quality = _quality_by_doc(result, view)
        if not quality:
            return None
        order = engine_order(p.pipeline for p in result.pipelines)
        engines = sorted(
            {p.pipeline for p in result.pipelines if p.view == view},
            key=lambda n: order[n],
        )
        # (quality, cer, support, accent) par (document, moteur) mesuré.
        raw: list[tuple[float, float, float, str]] = []
        for doc in result.documents:
            if doc.view != view or doc.pipeline not in order:
                continue
            q = quality.get(doc.document_id)
            if q is None:
                continue
            accent = engine_accent(order[doc.pipeline])
            for score in doc.scores:
                if score.metric == _METRIC and score.value is not None:
                    raw.append((q, score.value, float(score.support or 0), accent))
        if not raw:
            return None
        # Échelle Y commune : 0 (en bas) → max CER (en haut), pour exploiter la
        # hauteur quand tous les CER sont faibles. Le max est inscrit dans la légende.
        cer_max = max((cer for _q, cer, _s, _c in raw), default=0.0) or 1.0
        points = [
            (q, cer / cer_max, support, accent) for q, cer, support, accent in raw
        ]
        svg = bubble_chart(points)
        legend = " · ".join(
            f'<span class="eng-badge" style="--badge:{engine_accent(order[name])}">'
            f"{engine_letter(order[name])}</span> {escape(name)}"
            for name in engines
        )
        title = localized(ctx.lang, "Qualité × erreur", "Quality × error")
        intro = localized(
            ctx.lang,
            "Une bulle par document et moteur — <strong>X</strong> : qualité de "
            "l'image (gauche = dégradée) ; <strong>Y</strong> : CER (bas = 0, haut "
            f"= {cer_max * 100:.0f} %) ; <strong>taille</strong> ∝ nombre de "
            "caractères. Les bulles en haut à gauche = scans durs ; en bas à "
            "droite = faciles.",
            "One bubble per document and engine — <strong>X</strong>: image "
            "quality (left = degraded); <strong>Y</strong>: CER (bottom = 0, top = "
            f"{cer_max * 100:.0f} %); <strong>size</strong> ∝ character count. "
            "Bubbles top-left = hard scans; bottom-right = easy.",
        )
        return Html(
            f"<h2>{title}</h2>\n"
            f'<p class="muted">{intro}</p>\n'
            f'<div class="bubble-wrap">{svg}</div>\n'
            f'<p class="muted bubble-legend">{legend}</p>\n'
        )


__all__ = ["QualityErrorSection"]
