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


__all__ = ["bar_cell", "col_max", "format_value", "metric_th", "ordered_unique"]
