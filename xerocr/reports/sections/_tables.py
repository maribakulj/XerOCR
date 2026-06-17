"""Helpers de rendu **tabulaire** partagés par les sections (couche 7).

Mutualise (DRY) ce dont ``overview`` et ``by_document`` ont besoin : ordre stable
des vues, échelle de colonne et cellule **data-bar** dont la largeur est
**relative au max de sa colonne** (comparaison intra-métrique). Tout est
**déterministe** (division flottante IEEE-754 + ``round`` → même octet partout),
donc le rapport reste octet-stable.
"""

from __future__ import annotations

from collections.abc import Iterable

from xerocr.evaluation.result import MetricScore
from xerocr.reports.glossary import load_glossary
from xerocr.reports.html import escape


def ordered_unique(values: Iterable[str]) -> tuple[str, ...]:
    """Valeurs distinctes dans leur **ordre de première apparition**."""
    seen: list[str] = []
    for value in values:
        if value not in seen:
            seen.append(value)
    return tuple(seen)


def format_value(score: MetricScore) -> str:
    """Valeur formatée (``None`` non applicable → tiret)."""
    return "—" if score.value is None else f"{score.value:.4f}"


def col_max(rows: list[tuple[MetricScore, ...]], index: int) -> float:
    """Plus grande valeur (non ``None``) de la colonne → échelle des barres."""
    values = [v for r in rows if (v := r[index].value) is not None]
    return max(values) if values else 0.0


def nonempty_metric_indices(rows: list[tuple[MetricScore, ...]]) -> list[int]:
    """Indices de colonnes ayant **au moins une** valeur non ``None``.

    Une colonne tout-``None`` (métrique non applicable au corpus, ex. AIR/HCPR sur
    de la presse) n'apporte que des « — » : on la **masque** pour désencombrer.
    On distingue bien « tout None » (masqué) de « tout zéro » (gardé : c'est une
    vraie valeur)."""
    if not rows:
        return []
    return [
        i
        for i in range(len(rows[0]))
        if any(r[i].value is not None for r in rows)
    ]


def bar_cell(score: MetricScore, column_max: float, *, sortable: bool = False) -> str:
    """Cellule ``td.databar`` : barre relative à la colonne + valeur.

    ``sortable`` ajoute ``data-sort`` (valeur brute) → le tri client de
    ``report.js`` réordonne le DOM par cette clé (aucune donnée reconstruite)."""
    text = format_value(score)
    sort = (
        f' data-sort="{score.value:.6f}"'
        if sortable and score.value is not None
        else ""
    )
    if score.value is None or column_max <= 0:
        return f'<td class="databar"{sort}><span class="db-num">{text}</span></td>'
    width = round(score.value / column_max * 100)
    return (
        f'<td class="databar"{sort}>'
        f'<span class="db-fill" style="width:{width}%"></span>'
        f'<span class="db-num">{text}</span></td>'
    )


#: Groupes thématiques de métriques (ordre = ordre d'affichage canonique).
#: ``(clé, (libellé FR, EN), {métriques})`` — calque « Par moteur » du design.
_METRIC_GROUPS: tuple[tuple[str, tuple[str, str], frozenset[str]], ...] = (
    ("char", ("Erreur · caractère", "Character error"),
     frozenset({"cer", "cer_diplo", "cmer"})),
    ("accuracy", ("Exactitude", "Accuracy"),
     frozenset({"char_accuracy", "word_accuracy", "fca"})),
    ("word", ("Erreur · mot", "Word error"),
     frozenset({"wer", "mer", "wil"})),
    ("search", ("Recherche · sac de mots", "Bag-of-words search"),
     frozenset({"bow_precision", "bow_recall", "bow_f1"})),
    ("philo", ("Philologique", "Philological"),
     frozenset({"diacritic_err", "mufi_err"})),
    ("trust", ("Fiabilité documentaire", "Document reliability"),
     frozenset({"searchability", "hallucination", "air", "hcpr"})),
    ("struct", ("Structuré", "Structured"),
     frozenset({"numseq_strict", "numseq_value", "region_cer", "region_detection"})),
)
_GROUP_OF: dict[str, tuple[str, tuple[str, str]]] = {
    metric: (key, label)
    for key, label, members in _METRIC_GROUPS
    for metric in members
}


def group_header_row(
    metrics: list[str], lang: str, *, lead: int = 0, trail: int = 0
) -> str:
    """Rangée de **super-en-têtes** thématiques au-dessus des colonnes de métriques.

    Fusionne les métriques **consécutives** d'un même groupe en une cellule
    ``colspan`` (les profils sont déjà ordonnés par thème). ``lead``/``trail`` =
    nombre de colonnes hors-métrique à gauche/droite (#, moteur, dispersion…) →
    cellules vides de cadrage. Une métrique hors groupe connu → cellule vide."""
    cells: list[str] = []
    if lead:
        cells.append(f'<th colspan="{lead}"></th>')
    i = 0
    while i < len(metrics):
        entry = _GROUP_OF.get(metrics[i])
        if entry is None:
            cells.append("<th></th>")
            i += 1
            continue
        key, label = entry
        span = 1
        while i + span < len(metrics):
            nxt = _GROUP_OF.get(metrics[i + span])
            if nxt is None or nxt[0] != key:
                break
            span += 1
        text = label[1] if lang == "en" else label[0]
        cells.append(
            f'<th class="grp-head" colspan="{span}">{escape(text)}</th>'
        )
        i += span
    if trail:
        cells.append(f'<th colspan="{trail}"></th>')
    return f'<tr class="grp-row">{"".join(cells)}</tr>'


def bar_legend(lang: str) -> str:
    """Légende des barres de données (explique l'indicateur subtil sous les valeurs).

    Le canon montre une barre = **position sur l'axe de la métrique**, à **échelle
    commune par colonne** — sans légende, le lecteur ne sait pas ce qu'elle code."""
    fr = (
        '<p class="muted bar-legend">La barre sous chaque valeur indique sa '
        "position sur l'axe de la métrique — échelle commune par colonne.</p>\n"
    )
    en = (
        '<p class="muted bar-legend">The bar under each value shows its position '
        "on the metric's axis — common scale per column.</p>\n"
    )
    return en if lang == "en" else fr


def metric_th(metric: str, lang: str, *, sortable: bool = False) -> str:
    """En-tête de colonne de métrique : libellé + **définition au survol** (E1,
    depuis le glossaire) + **affordance de tri** (si ``sortable``).

    Le tri est câblé client-side par ``report.js`` (réordonne des lignes déjà
    rendues) ; sans JS, l'en-tête reste un libellé avec son ``title``."""
    entry = load_glossary(lang).get(metric)
    title = ""
    if entry:
        title = f"{entry.get('title', '')} — {entry.get('definition', '')}".strip(" —")
    title_attr = f' title="{escape(title)}"' if title else ""
    cls = "num-cell" + (" has-def" if title else "") + (" sortable" if sortable else "")
    arrow = ' <span class="th-sort" aria-hidden="true">↕</span>' if sortable else ""
    sort_attr = ' aria-sort="none"' if sortable else ""
    return f'<th class="{cls}"{title_attr}{sort_attr}>{escape(metric)}{arrow}</th>'


__all__ = [
    "bar_cell",
    "bar_legend",
    "col_max",
    "format_value",
    "group_header_row",
    "metric_th",
    "nonempty_metric_indices",
    "ordered_unique",
]
