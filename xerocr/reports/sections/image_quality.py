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
from xerocr.reports.html import escape, localized
from xerocr.reports.section import Html, SectionContext

#: Libellés FR des paliers (les clés du payload restent en anglais — contrat).
_TIER_LABELS = {"good": "bon", "medium": "moyen", "poor": "faible"}
#: Libellés EN des paliers (mêmes clés de payload — contrat inchangé).
_TIER_LABELS_EN = {"good": "good", "medium": "medium", "poor": "poor"}


def _tier_label(tier: str, lang: str) -> str:
    table = _TIER_LABELS_EN if lang == "en" else _TIER_LABELS
    return table.get(tier, tier)


def _quality_bar(value: float) -> str:
    """Cellule data-bar du score qualité (largeur = score, [0,1] → 0–100 %)."""
    width = round(value * 100)
    return (
        '<td class="databar">'
        f'<span class="db-fill" style="width:{width}%"></span>'
        f'<span class="db-num">{value:.2f}</span></td>'
    )


def _document_row(row: DocumentImageQuality, lang: str) -> str:
    tier = _tier_label(row.tier, lang)
    return (
        f"<tr><td>{escape(row.document_id)}</td>"
        f'<td class="disp">{row.sharpness:.2f}</td>'
        f'<td class="disp">{row.contrast:.2f}</td>'
        f'<td class="disp">{row.noise:.2f}</td>'
        f'<td class="disp">{row.rotation_degrees:+.1f}°</td>'
        f"{_quality_bar(row.quality_score)}"
        f'<td class="disp">{escape(tier)}</td></tr>'
    )


def _block(payload: ImageQualityPayload, lang: str) -> str:
    rows = "".join(_document_row(row, lang) for row in payload.documents)
    n = len(payload.documents)
    intro = localized(
        lang,
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
        "des seuils physiques. Les images distantes ou illisibles sont exclues.</p>\n",
        '<p class="muted">Image quality is a property of the <strong>corpus'
        "</strong>, measured once per document — independent of the engine that "
        "transcribes it. It helps tell a degraded scan apart from a weak engine "
        "when the CER rises. The four features are bounded to [0,1]: "
        "<strong>sharpness</strong> (Laplacian variance — blur crushes it), "
        "<strong>contrast</strong> (Michelson over the 5/95 percentiles, robust "
        "to extreme pixels), <strong>noise</strong> (median of gradients; "
        "lower = better), residual estimated <strong>skew</strong> "
        "(projection heuristic, bounded to ±5°). The <strong>quality score"
        "</strong> combines them (0.40·sharpness + 0.30·contrast + 0.20·(1−noise) + "
        "0.10·deskew); its weights and tiers (good ≥ 0.70 · medium "
        "≥ 0.40 · poor) are <strong>editorial conventions</strong>, not "
        "physical thresholds. Remote or unreadable images are excluded.</p>\n",
    )
    summary = localized(
        lang,
        '<p class="muted">'
        f"<strong>{n}</strong> image{'s' if n > 1 else ''} mesurée"
        f"{'s' if n > 1 else ''} · qualité moyenne "
        f"<strong>{payload.mean_quality:.2f}</strong> · netteté "
        f"{payload.mean_sharpness:.2f} · contraste {payload.mean_contrast:.2f} · "
        f"bruit {payload.mean_noise:.2f} · paliers : bon {payload.n_good} / "
        f"moyen {payload.n_medium} / faible {payload.n_poor}.</p>\n",
        '<p class="muted">'
        f"<strong>{n}</strong> image{'s' if n > 1 else ''} measured"
        " · mean quality "
        f"<strong>{payload.mean_quality:.2f}</strong> · sharpness "
        f"{payload.mean_sharpness:.2f} · contrast {payload.mean_contrast:.2f} · "
        f"noise {payload.mean_noise:.2f} · tiers: good {payload.n_good} / "
        f"medium {payload.n_medium} / poor {payload.n_poor}.</p>\n",
    )
    th_doc = localized(lang, "Document", "Document")
    th_sharp = localized(lang, "netteté", "sharpness")
    th_contrast = localized(lang, "contraste", "contrast")
    th_noise = localized(lang, "bruit", "noise")
    th_skew = localized(lang, "inclinaison", "skew")
    th_quality = localized(lang, "qualité", "quality")
    th_tier = localized(lang, "palier", "tier")
    return (
        f"{intro}"
        f"{summary}"
        f'<table class="data">\n<thead><tr><th>{th_doc}</th>'
        f'<th class="num-cell">{th_sharp}</th>'
        f'<th class="num-cell">{th_contrast}</th>'
        f'<th class="num-cell">{th_noise}</th>'
        f'<th class="num-cell">{th_skew}</th>'
        f'<th class="num-cell">{th_quality}</th><th>{th_tier}</th></tr></thead>\n'
        f"<tbody>{rows}</tbody>\n</table>\n"
    )


class ImageQualitySection:
    """Qualité mesurée des images du corpus, par document (lecture seule)."""

    name = "image_quality"
    requires: tuple[str, ...] = ()

    def render(self, result: RunResult, ctx: SectionContext) -> Html | None:
        blocks = [
            _block(analysis.payload, ctx.lang)
            for analysis in result.analyses
            if isinstance(analysis.payload, ImageQualityPayload)
        ]
        if not blocks:
            return None
        title = localized(ctx.lang, "Qualité des images", "Image quality")
        return Html(f"<h2>{title}</h2>\n" + "".join(blocks))


__all__ = ["ImageQualitySection"]
