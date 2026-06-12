"""Section philologie : préservation des marqueurs scribaux (couche 7).

Rend le payload ``philology`` en **lecture seule** : par pipeline et famille,
la part des signes abréviatifs de la GT reproduits **à l'identique** (strict)
vs **développés** (expansion), avec le détail par signe. La question éditoriale
diplomatique-vs-modernisante, que le CER global ne distingue pas.
"""

from __future__ import annotations

from xerocr.evaluation.analysis import PhilologyPayload, PipelinePhilology
from xerocr.evaluation.result import RunResult
from xerocr.reports.html import escape
from xerocr.reports.section import Html, SectionContext

_FAMILY_LABELS = {"abbreviations": "abréviations médiévales"}


def _share(numerator: int, denominator: int) -> str:
    return f"{numerator / denominator:.1%}" if denominator else "—"


def _pipeline_block(row: PipelinePhilology) -> str:
    family = _FAMILY_LABELS.get(row.family, row.family)
    signs = "".join(
        f'<tr><td class="disp">{escape(marker.sign)}</td>'
        f'<td class="disp">{marker.n_total}</td>'
        f'<td class="disp">{_share(marker.n_strict, marker.n_total)}</td>'
        f'<td class="disp">{_share(marker.n_expansion, marker.n_total)}</td></tr>'
        for marker in row.markers
    )
    return (
        f"<h4>{escape(row.pipeline)} — {escape(family)} : "
        f"{_share(row.n_strict, row.n_total)} strict · "
        f"{_share(row.n_expansion, row.n_total)} avec développement "
        f"({row.n_total} signes)</h4>\n"
        '<table class="data">\n<thead><tr><th>signe</th>'
        '<th class="num-cell">n</th><th class="num-cell">strict</th>'
        '<th class="num-cell">avec dév.</th></tr></thead>\n'
        f"<tbody>{signs}</tbody>\n</table>\n"
    )


def _block(view: str, payload: PhilologyPayload) -> str:
    return (
        f"<h3>{escape(view)} — marqueurs philologiques</h3>\n"
        '<p class="muted">« strict » = la forme abrégée de la vérité terrain '
        "est reproduite telle quelle (transcription diplomatique) ; « avec "
        "développement » = la forme ou son équivalent développé est présent "
        "(édition modernisante) — toujours ≥ strict, borne optimiste (un mot "
        "courant peut compter comme développement). Un écart fort entre les "
        "deux signale un moteur qui développe les abréviations.</p>\n"
        + "".join(_pipeline_block(row) for row in payload.pipelines)
    )


class PhilologySection:
    """Préservation des marqueurs scribaux, par pipeline et famille."""

    name = "philology"
    requires: tuple[str, ...] = ()

    def render(self, result: RunResult, ctx: SectionContext) -> Html | None:
        blocks = [
            _block(analysis.view, analysis.payload)
            for analysis in result.analyses
            if isinstance(analysis.payload, PhilologyPayload)
        ]
        if not blocks:
            return None
        return Html("<h2>Philologie</h2>\n" + "".join(blocks))


__all__ = ["PhilologySection"]
