"""Section qualité d'image : rend le payload ``image_quality`` au design.

Lecture seule du payload (aucun recalcul) : par document, les features mesurées
de la numérisation (netteté, contraste, bruit, inclinaison) et le score composite
+ son palier ; en tête, les moyennes corpus et la distribution des paliers.
**Scope corpus, par document** (≠ par pipeline) : une image est la même quel que
soit le moteur qui la transcrit. Pédagogie en prose (les constantes sont des
conventions éditoriales, pas des seuils physiques), aucun scalaire de classement
(pas de glossaire).
"""

from __future__ import annotations

from xerocr.evaluation.analysis import DocumentImageQuality, ImageQualityPayload
from xerocr.evaluation.result import RunResult
from xerocr.reports.html import escape
from xerocr.reports.section import Html, SectionContext

#: Libellés FR des paliers (les clés du payload restent en anglais — contrat).
_TIER_LABELS = {"good": "bon", "medium": "moyen", "poor": "faible"}


def _quality_bar(value: float) -> str:
    """Cellule data-bar du score qualité (largeur = score, [0,1] → 0–100 %)."""
    width = round(value * 100)
    return (
        '<td class="databar">'
        f'<span class="db-fill" style="width:{width}%"></span>'
        f'<span class="db-num">{value:.2f}</span></td>'
    )


def _document_row(row: DocumentImageQuality) -> str:
    tier = _TIER_LABELS.get(row.tier, row.tier)
    return (
        f"<tr><td>{escape(row.document_id)}</td>"
        f'<td class="disp">{row.sharpness:.2f}</td>'
        f'<td class="disp">{row.contrast:.2f}</td>'
        f'<td class="disp">{row.noise:.2f}</td>'
        f'<td class="disp">{row.rotation_degrees:+.1f}°</td>'
        f"{_quality_bar(row.quality_score)}"
        f'<td class="disp">{escape(tier)}</td></tr>'
    )


def _block(payload: ImageQualityPayload) -> str:
    rows = "".join(_document_row(row) for row in payload.documents)
    n = len(payload.documents)
    return (
        '<p class="muted">La qualité d\'image est une propriété du <strong>corpus'
        "</strong>, mesurée une fois par document — indépendante du moteur qui le "
        "transcrit. Elle aide à départager une numérisation dégradée d'un moteur "
        "faible quand le CER grimpe. Les quatre features sont bornées [0,1] : "
        "<strong>netteté</strong> (variance du laplacien — un flou l'écrase), "
        "<strong>contraste</strong> (Michelson sur les percentiles 5/95, robuste "
        "aux pixels extrêmes), <strong>bruit</strong> (médiane des gradients ; "
        "plus bas = mieux), <strong>inclinaison</strong> résiduelle estimée "
        "(heuristique de projection, bornée ±5°). Le <strong>score de qualité"
        "</strong> les combine (0,40·netteté + 0,30·contraste + 0,20·(1−bruit) + "
        "0,10·redressement) ; ses pondérations et ses paliers (bon ≥ 0,70 · moyen "
        "≥ 0,40 · faible) sont des <strong>conventions éditoriales</strong>, pas "
        "des seuils physiques. Les images distantes ou illisibles sont exclues.</p>\n"
        '<p class="muted">'
        f"<strong>{n}</strong> image{'s' if n > 1 else ''} mesurée"
        f"{'s' if n > 1 else ''} · qualité moyenne "
        f"<strong>{payload.mean_quality:.2f}</strong> · netteté "
        f"{payload.mean_sharpness:.2f} · contraste {payload.mean_contrast:.2f} · "
        f"bruit {payload.mean_noise:.2f} · paliers : bon {payload.n_good} / "
        f"moyen {payload.n_medium} / faible {payload.n_poor}.</p>\n"
        '<table class="data">\n<thead><tr><th>Document</th>'
        '<th class="num-cell">netteté</th><th class="num-cell">contraste</th>'
        '<th class="num-cell">bruit</th><th class="num-cell">inclinaison</th>'
        '<th class="num-cell">qualité</th><th>palier</th></tr></thead>\n'
        f"<tbody>{rows}</tbody>\n</table>\n"
    )


class ImageQualitySection:
    """Qualité mesurée des images du corpus, par document (lecture seule)."""

    name = "image_quality"
    requires: tuple[str, ...] = ()

    def render(self, result: RunResult, ctx: SectionContext) -> Html | None:
        blocks = [
            _block(analysis.payload)
            for analysis in result.analyses
            if isinstance(analysis.payload, ImageQualityPayload)
        ]
        if not blocks:
            return None
        return Html("<h2>Qualité des images</h2>\n" + "".join(blocks))


__all__ = ["ImageQualitySection"]
