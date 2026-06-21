"""Section qualité × erreur : **densité 2D** qualité d'image × CER (couche 7).

**X** = score de qualité de l'image, **Y** = CER (toutes combinaisons document ×
moteur confondues). Au lieu d'une bulle par point — qui explose à grand corpus —
les points sont **binnés en grille** : une bulle par cellule occupée, **taille ∝
nombre de points**. Le nuage est ainsi **borné** (au plus ``_GRID²`` bulles) et de
même allure à 20 ou 6000 documents, **sans rien retirer** (chaque couple est
compté). Révèle si les numérisations dégradées (gauche) tirent le CER vers le
haut. Pure présentation : lit le payload ``image_quality`` (par document) + les
CER du ``RunResult`` (aucun recalcul), SVG serveur déterministe, zéro JS.
"""

from __future__ import annotations

from xerocr.evaluation.analysis import ImageQualityPayload
from xerocr.evaluation.result import RunResult
from xerocr.reports._binning import density_grid
from xerocr.reports.html import localized
from xerocr.reports.section import Html, SectionContext
from xerocr.reports.sections._tables import ordered_unique
from xerocr.reports.svg import bubble_chart

_METRIC = "cer"
#: Côté de la grille de densité (constant → nombre de bulles borné, invariant).
_GRID = 24


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
    """Densité 2D qualité d'image × CER (document × moteur binnés en grille)."""

    name = "quality_error"
    requires: tuple[str, ...] = ()

    def render(self, result: RunResult, ctx: SectionContext) -> Html | None:
        if not result.pipelines:
            return None
        view = ordered_unique(p.view for p in result.pipelines)[0]
        quality = _quality_by_doc(result, view)
        if not quality:
            return None
        # (qualité, CER) par (document, moteur) mesuré — tous moteurs confondus.
        raw: list[tuple[float, float]] = []
        for doc in result.documents:
            if doc.view != view:
                continue
            q = quality.get(doc.document_id)
            if q is None:
                continue
            for score in doc.scores:
                if score.metric == _METRIC and score.value is not None:
                    raw.append((q, score.value))
        if not raw:
            return None
        # Échelle Y commune : 0 (bas) → max CER (haut), pour exploiter la hauteur
        # quand tous les CER sont faibles. Le max est inscrit dans la légende.
        cer_max = max(cer for _q, cer in raw) or 1.0
        cells = density_grid([(q, cer / cer_max) for q, cer in raw], _GRID, _GRID)
        points = [(cx, cy, count, "var(--ink)") for cx, cy, count in cells]
        svg = bubble_chart(points)
        title = localized(ctx.lang, "Qualité × erreur", "Quality × error")
        intro = localized(
            ctx.lang,
            f"Densité de {len(raw)} couples document × moteur — <strong>X</strong> : "
            "qualité de l'image (gauche = dégradée) ; <strong>Y</strong> : CER (bas = "
            f"0, haut = {cer_max * 100:.0f} %) ; <strong>taille</strong> de la bulle ∝ "
            "nombre de couples dans la cellule. Haut-gauche = scans durs ; bas-droite "
            "= faciles.",
            f"Density of {len(raw)} document × engine pairs — <strong>X</strong>: "
            "image quality (left = degraded); <strong>Y</strong>: CER (bottom = 0, top "
            f"= {cer_max * 100:.0f} %); bubble <strong>size</strong> ∝ pairs in the "
            "cell. Top-left = hard scans; bottom-right = easy.",
        )
        return Html(
            f"<h2>{title}</h2>\n"
            f'<p class="muted">{intro}</p>\n'
            f'<div class="bubble-wrap">{svg}</div>\n'
        )


__all__ = ["QualityErrorSection"]
