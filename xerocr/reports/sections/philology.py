"""Section philologie : préservation des marqueurs philologiques (couche 7).

Rend le payload ``philology`` en **lecture seule**. Deux lentilles selon la
famille : pour les **abréviations** scribales, la part des signes reproduits **à
l'identique** (strict) vs **développés** (expansion) ; pour la **typographie de
l'imprimé ancien**, la part des marqueurs restitués **à leur position**
(préservation, un seul score). La question éditoriale diplomatique-vs-modernisante,
que le CER global ne distingue pas.
"""

from __future__ import annotations

from xerocr.evaluation.analysis import PhilologyPayload, PipelinePhilology
from xerocr.evaluation.result import RunResult
from xerocr.reports.html import escape
from xerocr.reports.section import Html, SectionContext

_FAMILY_LABELS = {
    "abbreviations": "abréviations médiévales",
    "early_modern": "typographie de l'imprimé ancien",
}

#: Familles à préservation **positionnelle** : un seul score (le marqueur est à
#: sa place), sans lentille « développement ».
_POSITIONAL_FAMILIES = frozenset({"early_modern"})

#: Libellés lisibles des catégories typographiques de l'imprimé ancien.
_CATEGORY_LABELS = {
    "ligatures": "ligatures (ﬁ ﬂ ﬀ)",
    "long_s": "s long (ſ)",
    "dotless_i": "i sans point (ı)",
    "ampersand": "esperluette (&)",
    "nasal_tildes": "tildes nasaux (ã õ ñ)",
}


def _share(numerator: int, denominator: int) -> str:
    return f"{numerator / denominator:.1%}" if denominator else "—"


def _containment_block(row: PipelinePhilology, family: str) -> str:
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


def _positional_block(row: PipelinePhilology, family: str) -> str:
    cats = "".join(
        f'<tr><td class="disp">'
        f"{escape(_CATEGORY_LABELS.get(marker.sign, marker.sign))}</td>"
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
    return _containment_block(row, family)


def _block(view: str, payload: PhilologyPayload) -> str:
    return (
        f"<h3>{escape(view)} — marqueurs philologiques</h3>\n"
        '<p class="muted">Préservation des conventions de la vérité terrain que '
        "le CER global ne distingue pas. <b>Abréviations</b> : « strict » = la "
        "forme abrégée est reproduite telle quelle (diplomatique), « avec "
        "développement » = la forme ou son équivalent développé est présent "
        "(modernisant) — toujours ≥ strict, borne optimiste (un mot courant peut "
        "compter comme développement). <b>Imprimé ancien</b> : « préservé » = le "
        "marqueur typographique (ligature, s long, tilde nasal…) est restitué à "
        "sa position, selon le même alignement que le CER.</p>\n"
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
