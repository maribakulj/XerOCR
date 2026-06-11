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
from xerocr.reports.html import escape
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
            self._panel(result, view, name, order, engines, pos)
            for pos, name in enumerate(engines)
        )
        return Html(
            "<h2>Profil moteur</h2>\n"
            '<p class="muted">Cliquer un moteur dans le tableau ci-dessus pour '
            "ouvrir son profil détaillé.</p>\n"
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
        chart = (
            '<div class="prof-chart"><div class="prof-chart-title">CER par document '
            f'<span class="muted">· {len(cer_vals)} docs, triés</span></div>'
            f"{bar_series(cer_vals, accent=engine_accent(idx))}</div>"
            if cer_vals
            else ""
        )
        # Calibration + composition du moteur (réutilise les builders U2b/U2c),
        # en 2 colonnes ; chaque bloc n'apparaît que si sa donnée est présente.
        cal_block = (
            '<div class="prof-cell"><div class="prof-chart-title">Courbe de '
            f"calibration</div>{cal[1]}</div>"
            if cal is not None
            else ""
        )
        comp = _composition(result, view, name)
        comp_block = (
            '<div class="prof-cell"><div class="prof-chart-title">Composition des '
            f"erreurs</div>{comp}</div>"
            if comp
            else ""
        )
        extras = (
            f'<div class="prof-row">{cal_block}{comp_block}</div>'
            if (cal_block or comp_block)
            else ""
        )
        return (
            f'<div class="eng-profile" id="engine-{idx}" hidden '
            f'role="region" aria-label="{escape(name)}">'
            '<div class="prof-head">'
            '<a class="eng-back" href="#">← retour au tableau</a>'
            '<div class="prof-nav">'
            f'<a class="btn-sm" href="#engine-{prev_idx}">← précédent</a>'
            f'<a class="btn-sm" href="#engine-{next_idx}">suivant →</a></div></div>'
            f'<div class="prof-title"><span class="eng-badge" '
            f'style="--badge:{engine_accent(idx)}">{engine_letter(idx)}</span>'
            f"<span>{escape(name)}</span>"
            f'<span class="muted prof-pos">moteur {pos + 1} sur {total}</span></div>'
            f'<div class="kpi-band">{"".join(kpis)}</div>'
            f"{chart}{extras}</div>"
        )


__all__ = ["EngineProfileSection"]
