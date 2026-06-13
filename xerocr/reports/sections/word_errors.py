"""Section carte des mots : matrice mots × moteurs + regroupements (couche 7).

Lecture seule du payload ``word_errors`` : la **matière** derrière le CER — quels
mots de la vérité-terrain chaque moteur ne restitue pas, combien de fois, et
**comment ça se croise** (mots ratés par tous, par un seul, par certains). Une
heatmap SVG (compagnon **visuel**) double une **table accessible** qui porte la
matière (mots verbatim + comptes par moteur + recoupement) ; prose pédagogique
bilingue. Aucun scalaire de classement (pas de glossaire). Onglet « Croisements ».
"""

from __future__ import annotations

from collections.abc import Mapping

from xerocr.evaluation.analysis import WordError, WordErrorPayload
from xerocr.evaluation.result import RunResult
from xerocr.reports.engine_badges import engine_cell, engine_letter, engine_order
from xerocr.reports.html import escape
from xerocr.reports.section import Html, SectionContext
from xerocr.reports.svg import word_engine_heatmap

#: Lignes de la heatmap **visuelle** (les mots les plus ratés) — la table porte la
#: liste complète du payload (≤ 50). Borne la hauteur du graphe.
_HEATMAP_ROWS = 20

#: Teinte unique de la heatmap (intensité = compte) — accent neutre de la charte,
#: pas une couleur de moteur (la matrice teinte par fréquence, pas par identité).
_HEATMAP_ACCENT = "var(--fern)"

_TEXT: dict[str, dict[str, str]] = {
    "fr": {
        "title": "Carte des mots ratés",
        "subtitle": "mots de la vérité-terrain non restitués, par moteur",
        "intro": (
            "Quels mots de la vérité-terrain chaque moteur ne restitue pas — la "
            "matière brute derrière le CER. Case teintée = un moteur rate le mot ; "
            "le nombre = combien de fois. Les croisements montrent les mots durs "
            "pour <em>tous</em> les moteurs (la matière) vs propres à un seul (le "
            "moteur)."
        ),
        "caveats": (
            "L'appariement mot-à-mot dépend de la normalisation de la vue ; une "
            "fusion ou scission de mots est une limite connue de l'alignement. Les "
            "mots et les formes produites sont <strong>verbatim</strong> (rien "
            "d'inventé). Échantillon borné aux mots les plus ratés."
        ),
        "legend": "Moteurs",
        "th_word": "Mot (vérité-terrain)",
        "th_total": "total",
        "th_group": "recoupement",
        "graph_note": "Graphe : les {n} mots les plus ratés ; table : liste complète.",
        "u_universal": "tous",
        "u_engine_specific": "un seul",
        "u_partial": "plusieurs",
        "empty": "·",
    },
    "en": {
        "title": "Missed-word map",
        "subtitle": "ground-truth words not reproduced, per engine",
        "intro": (
            "Which ground-truth words each engine fails to reproduce — the raw "
            "matter behind the CER. A tinted cell = an engine misses the word; the "
            "number = how many times. The overlaps show words hard for <em>every</em> "
            "engine (the matter) vs specific to one (the engine)."
        ),
        "caveats": (
            "Word-to-word matching depends on the view's normalisation; a word "
            "merge or split is a known alignment limit. Words and produced forms "
            "are <strong>verbatim</strong> (nothing invented). Sample bounded to "
            "the most-missed words."
        ),
        "legend": "Engines",
        "th_word": "Word (ground truth)",
        "th_total": "total",
        "th_group": "overlap",
        "graph_note": "Graph: the {n} most-missed words; table: full list.",
        "u_universal": "all",
        "u_engine_specific": "one only",
        "u_partial": "several",
        "empty": "·",
    },
}


def _columns(payload: WordErrorPayload, order: Mapping[str, int]) -> list[str]:
    """Pipelines du payload, dans l'ordre stable des badges (identité moteur)."""
    return sorted(payload.pipelines, key=lambda name: order.get(name, len(order)))


def _matrix_row(
    word: WordError, columns: list[str], text: Mapping[str, str]
) -> str:
    """Ligne de la table : mot verbatim, compte par moteur, total, recoupement."""
    counts = {engine.pipeline: engine.count for engine in word.per_engine}
    cells = "".join(
        f'<td class="disp">{counts[name]}</td>'
        if name in counts
        else f'<td class="disp">{text["empty"]}</td>'
        for name in columns
    )
    return (
        f'<tr><td class="eng-cell">{escape(word.word)}</td>{cells}'
        f'<td class="disp">{word.total_errors}</td>'
        f'<td class="verdict">{escape(text[f"u_{word.group}"])}</td></tr>'
    )


def _block(
    view: str, payload: WordErrorPayload, order: Mapping[str, int], lang: str
) -> str:
    text = _TEXT.get(lang, _TEXT["fr"])
    columns = _columns(payload, order)
    legend = " · ".join(
        f"{engine_letter(order.get(name, 0))} {escape(name)}" for name in columns
    )
    letters = [engine_letter(order.get(name, 0)) for name in columns]
    heatmap_rows = []
    for word in payload.words[:_HEATMAP_ROWS]:
        counts = {engine.pipeline: engine.count for engine in word.per_engine}
        heatmap_rows.append((word.word, [counts.get(name, 0) for name in columns]))
    svg = word_engine_heatmap(letters, heatmap_rows, accent=_HEATMAP_ACCENT)
    headers = "".join(
        f'<th class="num-cell">{engine_cell(name, order.get(name, 0))}</th>'
        for name in columns
    )
    body = "".join(_matrix_row(word, columns, text) for word in payload.words)
    graph_note = text["graph_note"].format(n=min(_HEATMAP_ROWS, len(payload.words)))
    return (
        f"<h3>{escape(view)} — {text['subtitle']}</h3>\n"
        f'<p class="muted">{text["intro"]}</p>\n'
        f'<p class="muted">{text["legend"]} : {legend}</p>\n'
        f"{svg}\n"
        f'<p class="muted">{graph_note}</p>\n'
        '<table class="data">\n'
        f'<thead><tr><th>{text["th_word"]}</th>{headers}'
        f'<th class="num-cell">{text["th_total"]}</th>'
        f'<th>{text["th_group"]}</th></tr></thead>\n'
        f"<tbody>{body}</tbody>\n</table>\n"
        f'<p class="muted">{text["caveats"]}</p>\n'
    )


class WordErrorsSection:
    """Carte des mots ratés : matrice mots × moteurs + regroupements (lecture seule)."""

    name = "word_errors"
    requires: tuple[str, ...] = ()

    def render(self, result: RunResult, ctx: SectionContext) -> Html | None:
        order = engine_order(p.pipeline for p in result.pipelines)
        blocks = [
            _block(analysis.view, analysis.payload, order, ctx.lang)
            for analysis in result.analyses
            if isinstance(analysis.payload, WordErrorPayload)
        ]
        if not blocks:
            return None
        text = _TEXT.get(ctx.lang, _TEXT["fr"])
        return Html(f"<h2>{text['title']}</h2>\n" + "".join(blocks))


__all__ = ["WordErrorsSection"]
