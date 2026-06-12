"""Section philologie : préservation des marqueurs philologiques (couche 7).

Rend le payload ``philology`` en **lecture seule**. Deux lentilles selon la
famille : pour les **abréviations** scribales, la part des signes reproduits **à
l'identique** (strict) vs **développés** (expansion) ; pour la **typographie de
l'imprimé ancien**, la part des marqueurs restitués **à leur position**
(préservation, un seul score). La question éditoriale diplomatique-vs-modernisante,
que le CER global ne distingue pas.
"""

from __future__ import annotations

from xerocr.evaluation.analysis import (
    PhilologyPayload,
    PipelinePhilology,
    PipelineRomanNumerals,
    RomanNumeralsPayload,
)
from xerocr.evaluation.result import RunResult
from xerocr.reports.html import escape
from xerocr.reports.section import Html, SectionContext

#: Statuts romains : clé → libellé lisible (ordre de rendu).
_ROMAN_STATUS_LABELS = (
    ("strict_preserved", "forme stricte"),
    ("case_changed", "casse modifiée"),
    ("j_dropped", "j médiéval standardisé"),
    ("converted_to_arabic", "converti en arabe"),
    ("lost", "perdu"),
)

_FAMILY_LABELS = {
    "abbreviations": "abréviations médiévales",
    "early_modern": "typographie de l'imprimé ancien",
    "modern_archives": "archives modernes (XIXᵉ-XXᵉ)",
}

#: Familles à préservation **positionnelle** : un seul score (le marqueur est à
#: sa place), sans lentille « développement ».
_POSITIONAL_FAMILIES = frozenset({"early_modern"})

#: Familles dont les lignes sont des **catégories** (libellés lisibles), pas des
#: signes isolés.
_CATEGORY_FAMILIES = frozenset({"early_modern", "modern_archives"})

#: Libellés lisibles des catégories (imprimé ancien + archives modernes).
_CATEGORY_LABELS = {
    "ligatures": "ligatures (ﬁ ﬂ ﬀ)",
    "long_s": "s long (ſ)",
    "dotless_i": "i sans point (ı)",
    "ampersand": "esperluette (&)",
    "nasal_tildes": "tildes nasaux (ã õ ñ)",
    "civility_titles": "titres de civilité (Mme, Dr)",
    "ordinals": "ordinaux (1ᵉʳ, XIXᵉ)",
    "currency": "monnaies (₣, l., s., d.)",
    "administrative": "administratif (arr., dép.)",
    "civil_status": "état civil (°, †, ép.)",
    "typographic_punctuation": "ponctuation typographique (« » —)",
    "latin_abbr_modern": "abréviations latines (etc., cf.)",
    "bibliographic": "bibliographie (vol., p., n°)",
    "address": "adresse (bd, av., r.)",
}


def _share(numerator: int, denominator: int) -> str:
    return f"{numerator / denominator:.1%}" if denominator else "—"


def _item_label(sign: str, by_category: bool) -> str:
    return _CATEGORY_LABELS.get(sign, sign) if by_category else sign


def _containment_block(row: PipelinePhilology, family: str, by_category: bool) -> str:
    header = "catégorie" if by_category else "signe"
    items = "".join(
        f'<tr><td class="disp">{escape(_item_label(marker.sign, by_category))}</td>'
        f'<td class="disp">{marker.n_total}</td>'
        f'<td class="disp">{_share(marker.n_strict, marker.n_total)}</td>'
        f'<td class="disp">{_share(marker.n_expansion, marker.n_total)}</td></tr>'
        for marker in row.markers
    )
    return (
        f"<h4>{escape(row.pipeline)} — {escape(family)} : "
        f"{_share(row.n_strict, row.n_total)} strict · "
        f"{_share(row.n_expansion, row.n_total)} avec développement "
        f"({row.n_total} marqueurs)</h4>\n"
        f'<table class="data">\n<thead><tr><th>{header}</th>'
        '<th class="num-cell">n</th><th class="num-cell">strict</th>'
        '<th class="num-cell">avec dév.</th></tr></thead>\n'
        f"<tbody>{items}</tbody>\n</table>\n"
    )


def _positional_block(row: PipelinePhilology, family: str) -> str:
    cats = "".join(
        f'<tr><td class="disp">'
        f"{escape(_item_label(marker.sign, by_category=True))}</td>"
        f'<td class="disp">{marker.n_total}</td>'
        f'<td class="disp">{_share(marker.n_strict, marker.n_total)}</td></tr>'
        for marker in row.markers
    )
    return (
        f"<h4>{escape(row.pipeline)} — {escape(family)} : "
        f"{_share(row.n_strict, row.n_total)} préservé "
        f"({row.n_total} marqueurs)</h4>\n"
        '<table class="data">\n<thead><tr><th>catégorie</th>'
        '<th class="num-cell">n</th><th class="num-cell">préservé</th>'
        "</tr></thead>\n"
        f"<tbody>{cats}</tbody>\n</table>\n"
    )


def _pipeline_block(row: PipelinePhilology) -> str:
    family = _FAMILY_LABELS.get(row.family, row.family)
    if row.family in _POSITIONAL_FAMILIES:
        return _positional_block(row, family)
    return _containment_block(row, family, row.family in _CATEGORY_FAMILIES)


def _block(view: str, payload: PhilologyPayload) -> str:
    return (
        f"<h3>{escape(view)} — marqueurs philologiques</h3>\n"
        '<p class="muted">Préservation des conventions de la vérité terrain que '
        "le CER global ne distingue pas. <b>Abréviations</b> (médiévales, "
        "archives modernes) : « strict » = la forme abrégée est reproduite telle "
        "quelle (diplomatique), « avec développement » = la forme ou son "
        "équivalent développé est présent (modernisant) — toujours ≥ strict, "
        "borne optimiste (un mot courant peut compter comme développement). "
        "<b>Imprimé ancien</b> : « préservé » = le marqueur typographique "
        "(ligature, s long, tilde nasal…) est restitué à sa position, selon le "
        "même alignement que le CER.</p>\n"
        + "".join(_pipeline_block(row) for row in payload.pipelines)
    )


def _roman_pipeline_block(row: PipelineRomanNumerals) -> str:
    counts = {
        "strict_preserved": row.strict_preserved,
        "case_changed": row.case_changed,
        "j_dropped": row.j_dropped,
        "converted_to_arabic": row.converted_to_arabic,
        "lost": row.lost,
    }
    rows = "".join(
        f'<tr><td class="disp">{escape(label)}</td>'
        f'<td class="disp">{counts[key]}</td>'
        f'<td class="disp">{_share(counts[key], row.n_total)}</td></tr>'
        for key, label in _ROMAN_STATUS_LABELS
    )
    value_preserved = row.n_total - row.lost
    return (
        f"<h4>{escape(row.pipeline)} — numéraux romains : "
        f"{_share(row.strict_preserved, row.n_total)} strict · "
        f"{_share(value_preserved, row.n_total)} valeur préservée "
        f"({row.n_total} numéraux)</h4>\n"
        '<table class="data">\n<thead><tr><th>statut</th>'
        '<th class="num-cell">n</th><th class="num-cell">part</th>'
        "</tr></thead>\n"
        f"<tbody>{rows}</tbody>\n</table>\n"
    )


def _roman_block(view: str, payload: RomanNumeralsPayload) -> str:
    return (
        f"<h3>{escape(view)} — numéraux romains</h3>\n"
        '<p class="muted">Pour chaque numéral de la vérité terrain, comment '
        "l'OCR le restitue : forme stricte (diplomatique) · casse modifiée · "
        "« j » médiéval standardisé (viij → viii) · converti en chiffres arabes "
        "(XIV → 14) · perdu. « Valeur préservée » = tout sauf perdu.</p>\n"
        + "".join(_roman_pipeline_block(row) for row in payload.pipelines)
    )


class PhilologySection:
    """Préservation des marqueurs scribaux et numéraux romains, par pipeline."""

    name = "philology"
    requires: tuple[str, ...] = ()

    def render(self, result: RunResult, ctx: SectionContext) -> Html | None:
        blocks: list[str] = []
        for analysis in result.analyses:
            if isinstance(analysis.payload, PhilologyPayload):
                blocks.append(_block(analysis.view, analysis.payload))
            elif isinstance(analysis.payload, RomanNumeralsPayload):
                blocks.append(_roman_block(analysis.view, analysis.payload))
        if not blocks:
            return None
        return Html("<h2>Philologie</h2>\n" + "".join(blocks))


__all__ = ["PhilologySection"]
