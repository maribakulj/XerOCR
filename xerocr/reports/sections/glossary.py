"""Section glossaire : définitions pédagogiques des métriques présentes (couche 7).

Rend, en **fin de rapport**, une définition pour les **seules** métriques que le
``RunResult`` contient réellement (jamais en avance sur la donnée) et qui ont une
entrée dans le glossaire de la langue demandée. Affichage en **disclosure natif**
(``<details>``) : zéro JS, déterministe, autonome. Le contenu vient de la DONNÉE
``glossary/{lang}.yaml`` (anti-hallucination : aucune prose générée).
"""

from __future__ import annotations

from xerocr.evaluation.result import RunResult
from xerocr.reports.glossary import load_glossary
from xerocr.reports.html import escape
from xerocr.reports.section import Html, SectionContext

#: Champs affichés, dans un ordre stable (déterminisme). Une entrée absente est
#: simplement omise — pas d'erreur (les fichiers restent éditables sans casse).
_FIELDS: tuple[tuple[str, str, str], ...] = (
    ("definition", "Définition", "Definition"),
    ("measures", "Ce que ça mesure", "What it measures"),
    ("limits", "Limites", "Limits"),
)

_HEADINGS = {"fr": "Glossaire", "en": "Glossary"}
_INTROS = {
    "fr": "Définitions des métriques présentes dans ce rapport, pour le lecteur "
    "non spécialiste.",
    "en": "Definitions of the metrics present in this report, for the "
    "non-specialist reader.",
}


def _field_label(idx: int, lang: str) -> str:
    return _FIELDS[idx][2] if lang == "en" else _FIELDS[idx][1]


def _entry(term: dict[str, str], lang: str) -> str:
    title = term.get("title", "")
    rows = "".join(
        f'<dt class="gl-k">{escape(_field_label(i, lang))}</dt>'
        f'<dd class="gl-v">{escape(term[key])}</dd>'
        for i, (key, _, _) in enumerate(_FIELDS)
        if term.get(key)
    )
    return (
        '<details class="gl-item"><summary class="gl-term">'
        f"{escape(title)}</summary>\n"
        f'<dl class="gl-body">{rows}</dl></details>\n'
    )


class GlossarySection:
    """Glossaire des métriques **présentes**, en disclosure natif (zéro JS)."""

    name = "glossary"
    requires: tuple[str, ...] = ()

    def render(self, result: RunResult, ctx: SectionContext) -> Html | None:
        present = {
            score.metric
            for pipeline in result.pipelines
            for score in pipeline.aggregate
        }
        if not present:
            return None
        glossary = load_glossary(ctx.lang)
        # Ordre stable = ordre alphabétique des clés de métrique présentes.
        items = [
            _entry(glossary[metric], ctx.lang)
            for metric in sorted(present)
            if metric in glossary
        ]
        if not items:
            return None
        lang = ctx.lang if ctx.lang in _HEADINGS else "fr"
        heading = escape(_HEADINGS[lang])
        intro = escape(_INTROS[lang])
        return Html(
            f"<h2>{heading}</h2>\n"
            f'<p class="muted">{intro}</p>\n'
            f'<div class="glossary">{"".join(items)}</div>'
        )


__all__ = ["GlossarySection"]
