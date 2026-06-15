"""Section dispersion : étendue du CER par moteur, en **bandes SVG** (couche 7).

Visualise ce que ``by_engine`` montre en texte (min · médiane · max par document)
sous forme graphique — la **fiabilité** que l'agrégat masque. Échelle commune
entre moteurs (max global) → comparaison directe. Server-side, déterministe,
zéro JS. Donnée : ``RunResult.documents`` (CER par document, déjà calculé).
"""

from __future__ import annotations

from statistics import fmean, median

from xerocr.evaluation.result import RunDocumentResult, RunResult
from xerocr.reports.engine_badges import engine_accent, engine_letter, engine_order
from xerocr.reports.html import escape, localized
from xerocr.reports.section import Html, SectionContext
from xerocr.reports.sections._tables import ordered_unique
from xerocr.reports.svg import dispersion_strip

_METRIC = "cer"


def _per_doc_cer(
    documents: tuple[RunDocumentResult, ...], pipeline: str, view: str
) -> list[float]:
    return [
        score.value
        for doc in documents
        if doc.pipeline == pipeline and doc.view == view
        for score in doc.scores
        if score.metric == _METRIC and score.value is not None
    ]


def _pct(v: float) -> str:
    return f"{v * 100:.1f} %"


class DispersionSection:
    """Bandes de dispersion du CER par moteur (min·médiane·µ·max, échelle commune)."""

    name = "dispersion"
    requires: tuple[str, ...] = ()

    def render(self, result: RunResult, ctx: SectionContext) -> Html | None:
        if not result.documents:
            return None
        view = ordered_unique(d.view for d in result.documents)[0]
        order = engine_order(p.pipeline for p in result.pipelines) or engine_order(
            d.pipeline for d in result.documents
        )
        # (pipeline, valeurs) dans l'ordre canonique des badges.
        series: list[tuple[str, list[float]]] = []
        for pipeline in sorted(order, key=lambda p: order[p]):
            vals = _per_doc_cer(result.documents, pipeline, view)
            if vals:
                series.append((pipeline, vals))
        if not series:
            return None
        scale_max = max(max(v) for _, v in series)
        lang = ctx.lang
        rows = "".join(self._row(p, v, order[p], scale_max, lang) for p, v in series)
        title = localized(
            lang,
            f"Dispersion du CER (vue : {escape(view)})",
            f"CER dispersion (view: {escape(view)})",
        )
        intro = localized(
            lang,
            '<p class="muted">Étendue par document : min · médiane (disque) · '
            "moyenne (tick) · max. Échelle commune entre moteurs.</p>\n",
            '<p class="muted">Range per document: min · median (disc) · '
            "mean (tick) · max. Common scale across engines.</p>\n",
        )
        return Html(
            f"<h2>{title}</h2>\n"
            f"{intro}"
            f'<div class="disp-grid">{rows}</div>\n'
        )

    @staticmethod
    def _row(
        pipeline: str, vals: list[float], index: int, scale_max: float, lang: str
    ) -> str:
        lo, hi = min(vals), max(vals)
        med, mean = median(vals), fmean(vals)
        accent = engine_accent(index)
        strip = dispersion_strip(lo, med, mean, hi, scale_max, accent=accent)
        med_label = localized(lang, "méd", "med")
        return (
            '<div class="disp-row">'
            f'<div class="disp-head"><span class="eng-badge" style="--badge:{accent}">'
            f"{engine_letter(index)}</span>"
            f'<span class="disp-name">{escape(pipeline)}</span></div>'
            f"{strip}"
            '<div class="disp-labels mono">'
            f"min {_pct(lo)} · {med_label} {_pct(med)} · µ {_pct(mean)} · "
            f"max {_pct(hi)}"
            "</div></div>"
        )


__all__ = ["DispersionSection"]
