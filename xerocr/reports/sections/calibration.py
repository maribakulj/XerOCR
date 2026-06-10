"""Section calibration : fiabilité des confidences moteur (couche 7).

Rend les payloads ``calibration`` en **lecture seule** : ECE/MCE par pipeline
et table de fiabilité par bin (confiance annoncée vs exactitude observée).
"""

from __future__ import annotations

from xerocr.evaluation.analysis import CalibrationPayload
from xerocr.evaluation.result import RunResult
from xerocr.reports.html import escape
from xerocr.reports.section import Html, SectionContext


def _block(view: str, payload: CalibrationPayload) -> str:
    parts: list[str] = [f"<h3>{escape(view)} — calibration des confidences</h3>\n"]
    parts.append(
        '<p class="muted">Un moteur calibré a raison à hauteur de ce qu\'il '
        "annonce : ECE = écart moyen pondéré entre confiance et exactitude, "
        "MCE = écart maximal (plus bas = mieux).</p>\n"
    )
    for row in payload.pipelines:
        bins = "".join(
            f'<tr><td class="disp">[{b.lower:.1f} ; {b.upper:.1f}[</td>'
            f'<td class="disp">{b.mean_confidence:.3f}</td>'
            f'<td class="disp">{b.accuracy:.3f}</td>'
            f'<td class="disp">{b.count}</td></tr>'
            for b in row.bins
        )
        parts.append(
            f"<h4>{escape(row.pipeline)} — ECE {row.ece:.4f} · "
            f"MCE {row.mce:.4f} · {row.n_tokens} jetons</h4>\n"
            '<table class="data">\n<thead><tr><th>bin</th>'
            '<th class="num-cell">confiance moyenne</th>'
            '<th class="num-cell">exactitude</th>'
            '<th class="num-cell">jetons</th></tr></thead>\n'
            f"<tbody>{bins}</tbody>\n</table>\n"
        )
    return "".join(parts)


class CalibrationSection:
    """ECE/MCE + bins de fiabilité, par pipeline produisant des confidences."""

    name = "calibration"
    requires: tuple[str, ...] = ()

    def render(self, result: RunResult, ctx: SectionContext) -> Html | None:
        blocks = [
            _block(analysis.view, analysis.payload)
            for analysis in result.analyses
            if isinstance(analysis.payload, CalibrationPayload)
        ]
        if not blocks:
            return None
        return Html("<h2>Calibration</h2>\n" + "".join(blocks))


__all__ = ["CalibrationSection"]
