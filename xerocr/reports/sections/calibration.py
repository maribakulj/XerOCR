"""Section calibration : fiabilité des confidences moteur (couche 7).

Rend les payloads ``calibration`` en **lecture seule** : ECE/MCE par pipeline,
**courbe de fiabilité SVG** (confiance vs exactitude) et table par bin.
"""

from __future__ import annotations

from xerocr.evaluation.analysis import CalibrationPayload
from xerocr.evaluation.result import RunResult
from xerocr.reports.engine_badges import engine_accent, engine_order
from xerocr.reports.html import escape, localized
from xerocr.reports.section import Html, SectionContext
from xerocr.reports.svg import calibration_curve


def _block(
    view: str, payload: CalibrationPayload, order: dict[str, int], lang: str
) -> str:
    head = localized(
        lang,
        f"{escape(view)} — calibration des confidences",
        f"{escape(view)} — confidence calibration",
    )
    parts: list[str] = [f"<h3>{head}</h3>\n"]
    parts.append(
        localized(
            lang,
            '<p class="muted">Un moteur calibré a raison à hauteur de ce qu\'il '
            "annonce : la courbe suit la diagonale. ECE = écart moyen pondéré "
            "entre confiance et exactitude, MCE = écart maximal "
            "(plus bas = mieux).</p>\n",
            '<p class="muted">A calibrated engine is right as often as it '
            "claims: the curve follows the diagonal. ECE = mean weighted gap "
            "between confidence and accuracy, MCE = maximum gap "
            "(lower = better).</p>\n",
        )
    )
    tokens_word = localized(lang, "jetons", "tokens")
    conf_axis = localized(lang, "confiance →", "confidence →")
    th_bin = localized(lang, "bin", "bin")
    th_mean_conf = localized(lang, "confiance moyenne", "mean confidence")
    th_accuracy = localized(lang, "exactitude", "accuracy")
    th_tokens = localized(lang, "jetons", "tokens")
    for row in payload.pipelines:
        bins = "".join(
            f'<tr><td class="disp">[{b.lower:.1f} ; {b.upper:.1f}[</td>'
            f'<td class="disp">{b.mean_confidence:.3f}</td>'
            f'<td class="disp">{b.accuracy:.3f}</td>'
            f'<td class="disp">{b.count}</td></tr>'
            for b in row.bins
        )
        curve = calibration_curve(
            [(b.mean_confidence, b.accuracy) for b in row.bins],
            accent=engine_accent(order.get(row.pipeline, 0)),
        )
        parts.append(
            f"<h4>{escape(row.pipeline)} — ECE {row.ece:.4f} · "
            f"MCE {row.mce:.4f} · {row.n_tokens} {tokens_word}</h4>\n"
            '<div class="calib-block">'
            f'<div class="calib-plot">{curve}'
            f'<div class="calib-axis mono">{conf_axis}</div></div>'
            f'<table class="data">\n<thead><tr><th>{th_bin}</th>'
            f'<th class="num-cell">{th_mean_conf}</th>'
            f'<th class="num-cell">{th_accuracy}</th>'
            f'<th class="num-cell">{th_tokens}</th></tr></thead>\n'
            f"<tbody>{bins}</tbody>\n</table></div>\n"
        )
    return "".join(parts)


class CalibrationSection:
    """ECE/MCE + bins de fiabilité, par pipeline produisant des confidences."""

    name = "calibration"
    requires: tuple[str, ...] = ()

    def render(self, result: RunResult, ctx: SectionContext) -> Html | None:
        # Ordre canonique des moteurs (accent stable, partagé avec les sections).
        order = engine_order(p.pipeline for p in result.pipelines)
        blocks = [
            _block(analysis.view, analysis.payload, order, ctx.lang)
            for analysis in result.analyses
            if isinstance(analysis.payload, CalibrationPayload)
        ]
        if not blocks:
            return None
        title = localized(ctx.lang, "Calibration", "Calibration")
        return Html(f"<h2>{title}</h2>\n" + "".join(blocks))


__all__ = ["CalibrationSection"]
