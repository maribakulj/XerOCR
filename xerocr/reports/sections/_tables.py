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


def bar_cell(score: MetricScore, column_max: float) -> str:
    """Cellule ``td.databar`` : barre relative à la colonne + valeur."""
    text = format_value(score)
    if score.value is None or column_max <= 0:
        return f'<td class="databar"><span class="db-num">{text}</span></td>'
    width = round(score.value / column_max * 100)
    return (
        '<td class="databar">'
        f'<span class="db-fill" style="width:{width}%"></span>'
        f'<span class="db-num">{text}</span></td>'
    )


__all__ = ["bar_cell", "col_max", "format_value", "ordered_unique"]
