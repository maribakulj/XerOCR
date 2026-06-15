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
from xerocr.reports.html import escape, localized
from xerocr.reports.section import Html, SectionContext

#: Statuts romains : clé → libellé lisible bilingue (ordre de rendu).
_ROMAN_STATUS_LABELS: tuple[tuple[str, str, str], ...] = (
    ("strict_preserved", "forme stricte", "strict form"),
    ("case_changed", "casse modifiée", "case changed"),
    ("j_dropped", "j médiéval standardisé", "medieval j standardized"),
    ("converted_to_arabic", "converti en arabe", "converted to Arabic"),
    ("lost", "perdu", "lost"),
)

_FAMILY_LABELS: dict[str, tuple[str, str]] = {
    "abbreviations": ("abréviations médiévales", "medieval abbreviations"),
    "early_modern": (
        "typographie de l'imprimé ancien",
        "early modern print typography",
    ),
    "modern_archives": (
        "archives modernes (XIXᵉ-XXᵉ)",
        "modern archives (19th-20th c.)",
    ),
}

#: Familles à préservation **positionnelle** : un seul score (le marqueur est à
#: sa place), sans lentille « développement ».
_POSITIONAL_FAMILIES = frozenset({"early_modern"})

#: Familles dont les lignes sont des **catégories** (libellés lisibles), pas des
#: signes isolés.
_CATEGORY_FAMILIES = frozenset({"early_modern", "modern_archives"})

#: Libellés lisibles bilingues des catégories (imprimé ancien + archives
#: modernes). Les glyphes entre parenthèses sont des données verbatim.
_CATEGORY_LABELS: dict[str, tuple[str, str]] = {
    "ligatures": ("ligatures (ﬁ ﬂ ﬀ)", "ligatures (ﬁ ﬂ ﬀ)"),
    "long_s": ("s long (ſ)", "long s (ſ)"),
    "dotless_i": ("i sans point (ı)", "dotless i (ı)"),
    "ampersand": ("esperluette (&)", "ampersand (&)"),
    "nasal_tildes": ("tildes nasaux (ã õ ñ)", "nasal tildes (ã õ ñ)"),
    "civility_titles": (
        "titres de civilité (Mme, Dr)",
        "civility titles (Mme, Dr)",
    ),
    "ordinals": ("ordinaux (1ᵉʳ, XIXᵉ)", "ordinals (1ᵉʳ, XIXᵉ)"),
    "currency": ("monnaies (₣, l., s., d.)", "currency (₣, l., s., d.)"),
    "administrative": ("administratif (arr., dép.)", "administrative (arr., dép.)"),
    "civil_status": ("état civil (°, †, ép.)", "civil status (°, †, ép.)"),
    "typographic_punctuation": (
        "ponctuation typographique (« » —)",
        "typographic punctuation (« » —)",
    ),
    "latin_abbr_modern": (
        "abréviations latines (etc., cf.)",
        "Latin abbreviations (etc., cf.)",
    ),
    "bibliographic": ("bibliographie (vol., p., n°)", "bibliography (vol., p., n°)"),
    "address": ("adresse (bd, av., r.)", "address (bd, av., r.)"),
}


def _share(numerator: int, denominator: int) -> str:
    return f"{numerator / denominator:.1%}" if denominator else "—"


def _item_label(sign: str, by_category: bool, lang: str) -> str:
    if by_category and sign in _CATEGORY_LABELS:
        return localized(lang, *_CATEGORY_LABELS[sign])
    return sign


def _containment_block(
    row: PipelinePhilology, family: str, by_category: bool, lang: str
) -> str:
    header = localized(lang, "catégorie" if by_category else "signe",
                       "category" if by_category else "sign")
    items = "".join(
        f'<tr><td class="disp">'
        f"{escape(_item_label(marker.sign, by_category, lang))}</td>"
        f'<td class="disp">{marker.n_total}</td>'
        f'<td class="disp">{_share(marker.n_strict, marker.n_total)}</td>'
        f'<td class="disp">{_share(marker.n_expansion, marker.n_total)}</td></tr>'
        for marker in row.markers
    )
    head = localized(
        lang,
        f"{escape(row.pipeline)} — {escape(family)} : "
        f"{_share(row.n_strict, row.n_total)} strict · "
        f"{_share(row.n_expansion, row.n_total)} avec développement "
        f"({row.n_total} marqueurs)",
        f"{escape(row.pipeline)} — {escape(family)}: "
        f"{_share(row.n_strict, row.n_total)} strict · "
        f"{_share(row.n_expansion, row.n_total)} with expansion "
        f"({row.n_total} markers)",
    )
    th_n = localized(lang, "n", "n")
    th_strict = localized(lang, "strict", "strict")
    th_expansion = localized(lang, "avec dév.", "with exp.")
    return (
        f"<h4>{head}</h4>\n"
        f'<table class="data">\n<thead><tr><th>{header}</th>'
        f'<th class="num-cell">{th_n}</th><th class="num-cell">{th_strict}</th>'
        f'<th class="num-cell">{th_expansion}</th></tr></thead>\n'
        f"<tbody>{items}</tbody>\n</table>\n"
    )


def _positional_block(row: PipelinePhilology, family: str, lang: str) -> str:
    cats = "".join(
        f'<tr><td class="disp">'
        f"{escape(_item_label(marker.sign, True, lang))}</td>"
        f'<td class="disp">{marker.n_total}</td>'
        f'<td class="disp">{_share(marker.n_strict, marker.n_total)}</td></tr>'
        for marker in row.markers
    )
    head = localized(
        lang,
        f"{escape(row.pipeline)} — {escape(family)} : "
        f"{_share(row.n_strict, row.n_total)} préservé "
        f"({row.n_total} marqueurs)",
        f"{escape(row.pipeline)} — {escape(family)}: "
        f"{_share(row.n_strict, row.n_total)} preserved "
        f"({row.n_total} markers)",
    )
    th_category = localized(lang, "catégorie", "category")
    th_n = localized(lang, "n", "n")
    th_preserved = localized(lang, "préservé", "preserved")
    return (
        f"<h4>{head}</h4>\n"
        f'<table class="data">\n<thead><tr><th>{th_category}</th>'
        f'<th class="num-cell">{th_n}</th><th class="num-cell">{th_preserved}</th>'
        "</tr></thead>\n"
        f"<tbody>{cats}</tbody>\n</table>\n"
    )


def _pipeline_block(row: PipelinePhilology, lang: str) -> str:
    family = localized(lang, *_FAMILY_LABELS[row.family]) \
        if row.family in _FAMILY_LABELS else row.family
    if row.family in _POSITIONAL_FAMILIES:
        return _positional_block(row, family, lang)
    return _containment_block(row, family, row.family in _CATEGORY_FAMILIES, lang)


def _block(view: str, payload: PhilologyPayload, lang: str) -> str:
    head = localized(
        lang,
        f"{escape(view)} — marqueurs philologiques",
        f"{escape(view)} — philological markers",
    )
    prose = localized(
        lang,
        '<p class="muted">Préservation des conventions de la vérité terrain que '
        "le CER global ne distingue pas. <b>Abréviations</b> (médiévales, "
        "archives modernes) : « strict » = la forme abrégée est reproduite telle "
        "quelle (diplomatique), « avec développement » = la forme ou son "
        "équivalent développé est présent (modernisant) — toujours ≥ strict, "
        "borne optimiste (un mot courant peut compter comme développement). "
        "<b>Imprimé ancien</b> : « préservé » = le marqueur typographique "
        "(ligature, s long, tilde nasal…) est restitué à sa position, selon le "
        "même alignement que le CER.</p>\n",
        '<p class="muted">Preservation of ground-truth conventions that '
        "the global CER does not distinguish. <b>Abbreviations</b> (medieval, "
        "modern archives): « strict » = the abbreviated form is reproduced as "
        "is (diplomatic), « with expansion » = the form or its "
        "expanded equivalent is present (modernizing) — always ≥ strict, "
        "an optimistic bound (a common word may count as an expansion). "
        "<b>Early modern print</b>: « preserved » = the typographic marker "
        "(ligature, long s, nasal tilde…) is restored at its position, under the "
        "same alignment as the CER.</p>\n",
    )
    return (
        f"<h3>{head}</h3>\n"
        + prose
        + "".join(_pipeline_block(row, lang) for row in payload.pipelines)
    )


def _roman_pipeline_block(row: PipelineRomanNumerals, lang: str) -> str:
    counts = {
        "strict_preserved": row.strict_preserved,
        "case_changed": row.case_changed,
        "j_dropped": row.j_dropped,
        "converted_to_arabic": row.converted_to_arabic,
        "lost": row.lost,
    }
    rows = "".join(
        f'<tr><td class="disp">{escape(localized(lang, label_fr, label_en))}</td>'
        f'<td class="disp">{counts[key]}</td>'
        f'<td class="disp">{_share(counts[key], row.n_total)}</td></tr>'
        for key, label_fr, label_en in _ROMAN_STATUS_LABELS
    )
    value_preserved = row.n_total - row.lost
    head = localized(
        lang,
        f"{escape(row.pipeline)} — numéraux romains : "
        f"{_share(row.strict_preserved, row.n_total)} strict · "
        f"{_share(value_preserved, row.n_total)} valeur préservée "
        f"({row.n_total} numéraux)",
        f"{escape(row.pipeline)} — Roman numerals: "
        f"{_share(row.strict_preserved, row.n_total)} strict · "
        f"{_share(value_preserved, row.n_total)} value preserved "
        f"({row.n_total} numerals)",
    )
    th_status = localized(lang, "statut", "status")
    th_n = localized(lang, "n", "n")
    th_share = localized(lang, "part", "share")
    return (
        f"<h4>{head}</h4>\n"
        f'<table class="data">\n<thead><tr><th>{th_status}</th>'
        f'<th class="num-cell">{th_n}</th><th class="num-cell">{th_share}</th>'
        "</tr></thead>\n"
        f"<tbody>{rows}</tbody>\n</table>\n"
    )


def _roman_block(view: str, payload: RomanNumeralsPayload, lang: str) -> str:
    head = localized(
        lang,
        f"{escape(view)} — numéraux romains",
        f"{escape(view)} — Roman numerals",
    )
    prose = localized(
        lang,
        '<p class="muted">Pour chaque numéral de la vérité terrain, comment '
        "l'OCR le restitue : forme stricte (diplomatique) · casse modifiée · "
        "« j » médiéval standardisé (viij → viii) · converti en chiffres arabes "
        "(XIV → 14) · perdu. « Valeur préservée » = tout sauf perdu.</p>\n",
        '<p class="muted">For each ground-truth numeral, how '
        "the OCR restores it: strict form (diplomatic) · case changed · "
        "medieval « j » standardized (viij → viii) · converted to Arabic numerals "
        "(XIV → 14) · lost. « Value preserved » = everything but lost.</p>\n",
    )
    return (
        f"<h3>{head}</h3>\n"
        + prose
        + "".join(_roman_pipeline_block(row, lang) for row in payload.pipelines)
    )


class PhilologySection:
    """Préservation des marqueurs scribaux et numéraux romains, par pipeline."""

    name = "philology"
    requires: tuple[str, ...] = ()

    def render(self, result: RunResult, ctx: SectionContext) -> Html | None:
        blocks: list[str] = []
        for analysis in result.analyses:
            if isinstance(analysis.payload, PhilologyPayload):
                blocks.append(_block(analysis.view, analysis.payload, ctx.lang))
            elif isinstance(analysis.payload, RomanNumeralsPayload):
                blocks.append(
                    _roman_block(analysis.view, analysis.payload, ctx.lang)
                )
        if not blocks:
            return None
        title = localized(ctx.lang, "Philologie", "Philology")
        return Html(f"<h2>{title}</h2>\n" + "".join(blocks))


__all__ = ["PhilologySection"]
