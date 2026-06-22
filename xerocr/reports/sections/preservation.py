"""Section « Signaux patrimoniaux » — préservation des caractères patrimoniaux
(couche 7).

Surface, comme **faits mesurés** (aucun verdict), les taux de préservation que le
CER global agrège et que le tableau de comparaison disperse en colonnes : MUFI,
diacritiques, archaïsmes curés (HCPR) et sur-historicisation (AIR). Lecture seule ;
chaque mesure porte son **critère exact** (la part de quoi, mesurée sur quoi). Les
moteurs sont rangés par **identité stable** (ordre d'apparition), pas par rang.
"""

from __future__ import annotations

from xerocr.evaluation.result import PipelineResult, RunResult
from xerocr.reports.engine_badges import engine_cell, engine_order
from xerocr.reports.html import escape, localized, view_prefix
from xerocr.reports.section import Html, SectionContext
from xerocr.reports.sections._tables import ordered_unique

#: Mesures patrimoniales : ``(clé, higher_is_better, libellé FR, EN, critère FR,
#: critère EN)``. Le critère **mène** le libellé (le nom porte son calcul). Ordre =
#: ordre d'affichage des colonnes.
_SIGNALS: tuple[tuple[str, bool, str, str, str, str], ...] = (
    (
        "diacritic_err", False, "Erreur diacritiques", "Diacritic error",
        "part des signes diacritiques de la vérité terrain mal restitués",
        "share of ground-truth diacritics mis-restored",
    ),
    (
        "mufi_err", False, "Erreur MUFI", "MUFI error",
        "part des caractères médiévaux (MUFI) de la vérité terrain mal restitués",
        "share of ground-truth medieval (MUFI) characters mis-restored",
    ),
    (
        "hcpr", True, "Préservation archaïsmes (HCPR)", "Archaism preservation (HCPR)",
        "part des caractères archaïques d'une liste curée présents dans la sortie",
        "share of curated archaic characters present in the output",
    ),
    (
        "air", False, "Apport d'archaïsmes (AIR)", "Archaism insertion (AIR)",
        "part des caractères archaïques de la **sortie** insérés sans appui dans "
        "la vérité terrain (sur-historicisation)",
        "share of archaic characters in the **output** inserted with no "
        "ground-truth support (over-historicization)",
    ),
)


def _val(pipeline: PipelineResult, metric: str) -> float | None:
    return next((s.value for s in pipeline.aggregate if s.metric == metric), None)


def _table(
    view: str,
    rows: list[PipelineResult],
    present: list[tuple[str, bool, str, str, str, str]],
    order: dict[str, int],
    lang: str,
    multi: bool,
) -> str:
    prefix = view_prefix(view, lang, multi=multi)
    head = localized(lang, f"{prefix}préservation", f"{prefix}preservation")
    th_eng = localized(lang, "moteur", "engine")
    headers = "".join(
        f'<th class="num-cell">'
        f'{escape(localized(lang, fr, en))} {"↑" if hib else "↓"}</th>'
        for _k, hib, fr, en, _cf, _ce in present
    )
    body: list[str] = []
    for pipeline in sorted(rows, key=lambda p: order.get(p.pipeline, 0)):
        idx = order.get(pipeline.pipeline, 0)
        cells = "".join(
            f'<td class="disp">'
            f'{(f"{v:.1%}" if (v := _val(pipeline, k)) is not None else "—")}</td>'
            for k, _h, _fr, _en, _cf, _ce in present
        )
        body.append(
            f'<tr><td class="eng-cell">{engine_cell(pipeline.pipeline, idx)}</td>'
            f"{cells}</tr>"
        )
    return (
        f"<h3>{head}</h3>\n"
        f'<table class="data compact">\n<thead><tr><th>{th_eng}</th>'
        f"{headers}</tr></thead>\n<tbody>{''.join(body)}</tbody>\n</table>\n"
    )


def _criteria(present: list[tuple[str, bool, str, str, str, str]], lang: str) -> str:
    """Légende : le **critère exact** de chaque signal présent (fait mesuré)."""
    items = " · ".join(
        f"<strong>{escape(localized(lang, fr, en))}</strong> : "
        f"{localized(lang, cf, ce)}"
        for _k, _h, fr, en, cf, ce in present
    )
    note = localized(
        lang,
        "↓ = plus bas est meilleur · ↑ = plus haut est meilleur. Mesures, pas "
        "verdict : aucun gagnant n'est déclaré.",
        "↓ = lower is better · ↑ = higher is better. Measurements, not a "
        "verdict: no winner is declared.",
    )
    return f'<p class="muted">{items}. {note}</p>\n'


class PreservationSection:
    """Taux de préservation patrimoniale par moteur (MUFI, diacritiques, HCPR, AIR)."""

    name = "preservation"
    requires: tuple[str, ...] = ()

    def render(self, result: RunResult, ctx: SectionContext) -> Html | None:
        if not result.pipelines:
            return None
        order = engine_order(p.pipeline for p in result.pipelines)
        views = ordered_unique(p.view for p in result.pipelines)
        multi = len(views) > 1
        lang = ctx.lang
        blocks: list[str] = []
        legend = ""
        for view in views:
            rows = [p for p in result.pipelines if p.view == view]
            present = [
                s for s in _SIGNALS
                if any(_val(p, s[0]) is not None for p in rows)
            ]
            if not present:
                continue
            if not legend:  # un seul rappel de critère, en tête
                legend = _criteria(present, lang)
            blocks.append(_table(view, rows, present, order, lang, multi))
        if not blocks:
            return None  # aucune mesure patrimoniale dans ce run → pas de section vide
        title = localized(lang, "Signaux patrimoniaux", "Heritage signals")
        return Html(f"<h2>{title}</h2>\n{legend}{''.join(blocks)}")


__all__ = ["PreservationSection"]
