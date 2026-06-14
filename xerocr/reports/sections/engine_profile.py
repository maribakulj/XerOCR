"""Section profil moteur : panneaux **drill-in** par moteur (couche 7).

Pour chaque moteur, un panneau **caché** (révélé au clic d'une ligne du tableau
de classement, ancre ``#engine-<idx>``) : bande KPI (CER/WER/… de l'agrégat,
ECE si calibration) + **CER par document** trié (barres SVG). Enrichissement
progressif : sans JS, le panneau s'affiche via ``:target`` ; ``report.js`` le
révèle en masquant les autres (← retour, précédent/suivant). Server-side,
déterministe, zéro donnée reconstruite. Réutilise les builders SVG (U2).
"""

from __future__ import annotations

from xerocr.evaluation.analysis import CalibrationPayload, TaxonomyPayload
from xerocr.evaluation.result import PipelineResult, RunResult
from xerocr.reports.engine_badges import engine_accent, engine_letter, engine_order
from xerocr.reports.html import escape, localized
from xerocr.reports.section import Html, SectionContext
from xerocr.reports.sections._tables import ordered_unique
from xerocr.reports.sections.taxonomy import composition_html
from xerocr.reports.svg import bar_series, calibration_curve

_METRIC = "cer"


def _per_doc_cer(result: RunResult, pipeline: str, view: str) -> list[float]:
    return [
        score.value
        for doc in result.documents
        if doc.pipeline == pipeline and doc.view == view
        for score in doc.scores
        if score.metric == _METRIC and score.value is not None
    ]


def _calibration(
    result: RunResult, view: str, pipeline: str
) -> tuple[float, str] | None:
    """(ECE, courbe SVG) du moteur si calibration présente, sinon ``None``."""
    for analysis in result.analyses:
        payload = analysis.payload
        if analysis.view == view and isinstance(payload, CalibrationPayload):
            for row in payload.pipelines:
                if row.pipeline == pipeline:
                    curve = calibration_curve(
                        [(b.mean_confidence, b.accuracy) for b in row.bins],
                        accent="var(--fern)",
                    )
                    return row.ece, curve
    return None


def _composition(result: RunResult, view: str, pipeline: str) -> str:
    """Composition d'erreurs du moteur (réutilise ``taxonomy.composition_html``)."""
    for analysis in result.analyses:
        payload = analysis.payload
        if analysis.view == view and isinstance(payload, TaxonomyPayload):
            for row in payload.pipelines:
                if row.pipeline == pipeline:
                    return composition_html(payload.classes, row)
    return ""


def _kpi(label: str, value: str) -> str:
    return (
        f'<div class="kpi"><div class="kpi-k">{escape(label)}</div>'
        f'<div class="kpi-v">{escape(value)}</div></div>'
    )


def _pct(v: float) -> str:
    return f"{v * 100:.1f} %"


class EngineProfileSection:
    """Panneaux profil par moteur (KPIs + CER/document), révélés au clic."""

    name = "engine_profiles"
    requires: tuple[str, ...] = ()

    def render(self, result: RunResult, ctx: SectionContext) -> Html | None:
        if not result.pipelines:
            return None
        view = ordered_unique(p.view for p in result.pipelines)[0]
        order = engine_order(p.pipeline for p in result.pipelines)
        view_pipes = {p.pipeline: p for p in result.pipelines if p.view == view}
        engines = [n for n in sorted(order, key=lambda n: order[n]) if n in view_pipes]
        if not engines:
            return None
        panels = "".join(
            self._panel(result, view, name, order, engines, pos, ctx.lang)
            for pos, name in enumerate(engines)
        )
        return Html(
            f"<h2>{localized(ctx.lang, 'Profil moteur', 'Engine profile')}</h2>\n"
            '<p class="muted">'
            + localized(
                ctx.lang,
                "Cliquer un moteur dans le tableau ci-dessus pour "
                "ouvrir son profil détaillé.",
                "Click an engine in the table above to "
                "open its detailed profile.",
            )
            + "</p>\n"
            f'<div class="eng-profiles">{panels}</div>\n'
        )

    def _panel(
        self,
        result: RunResult,
        view: str,
        name: str,
        order: dict[str, int],
        engines: list[str],
        pos: int,
        lang: str,
    ) -> str:
        idx = order[name]
        pipe: PipelineResult = next(
            p for p in result.pipelines if p.view == view and p.pipeline == name
        )
        total = len(engines)
        prev_idx = order[engines[(pos - 1) % total]]
        next_idx = order[engines[(pos + 1) % total]]
        # KPIs : métriques d'agrégat (réelles) + ECE si calibration présente.
        kpis = [
            _kpi(s.metric, _pct(s.value))
            for s in pipe.aggregate
            if s.value is not None
        ]
        cal = _calibration(result, view, name)
        if cal is not None:
            kpis.append(_kpi("ece", _pct(cal[0])))
        cer_vals = sorted(_per_doc_cer(result, name, view))
        chart_caption = localized(
            lang,
            f'<span class="muted">· {len(cer_vals)} docs, triés</span>',
            f'<span class="muted">· {len(cer_vals)} docs, sorted</span>',
        )
        chart = (
            '<div class="prof-chart"><div class="prof-chart-title">'
            + localized(lang, "CER par document ", "CER per document ")
            + f"{chart_caption}</div>"
            f"{bar_series(cer_vals, accent=engine_accent(idx))}</div>"
            if cer_vals
            else ""
        )
        # Calibration + composition du moteur (réutilise les builders U2b/U2c),
        # en 2 colonnes ; chaque bloc n'apparaît que si sa donnée est présente.
        cal_block = (
            '<div class="prof-cell"><div class="prof-chart-title">'
            + localized(lang, "Courbe de calibration", "Calibration curve")
            + f"</div>{cal[1]}</div>"
            if cal is not None
            else ""
        )
        comp = _composition(result, view, name)
        comp_block = (
            '<div class="prof-cell"><div class="prof-chart-title">'
            + localized(lang, "Composition des erreurs", "Error composition")
            + f"</div>{comp}</div>"
            if comp
            else ""
        )
        extras = (
            f'<div class="prof-row">{cal_block}{comp_block}</div>'
            if (cal_block or comp_block)
            else ""
        )
        back_label = localized(lang, "← retour au tableau", "← back to table")
        prev_label = localized(lang, "← précédent", "← previous")
        next_label = localized(lang, "suivant →", "next →")
        pos_label = localized(
            lang,
            f"moteur {pos + 1} sur {total}",
            f"engine {pos + 1} of {total}",
        )
        return (
            f'<div class="drill-panel eng-profile" id="engine-{idx}" hidden '
            f'role="region" aria-label="{escape(name)}">'
            '<div class="prof-head">'
            f'<a class="drill-back" href="#">{back_label}</a>'
            '<div class="prof-nav">'
            f'<a class="btn-sm" href="#engine-{prev_idx}">{prev_label}</a>'
            f'<a class="btn-sm" href="#engine-{next_idx}">{next_label}</a></div></div>'
            f'<div class="prof-title"><span class="eng-badge" '
            f'style="--badge:{engine_accent(idx)}">{engine_letter(idx)}</span>'
            f"<span>{escape(name)}</span>"
            f'<span class="muted prof-pos">{pos_label}</span></div>'
            f'<div class="kpi-band">{"".join(kpis)}</div>'
            f"{chart}{extras}</div>"
        )


__all__ = ["EngineProfileSection"]
