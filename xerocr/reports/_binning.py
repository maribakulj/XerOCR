"""Binning de distributions pour les graphes du rapport (couche 7).

Agréger plutôt qu'énumérer : un histogramme (1D) ou une grille de densité (2D)
a la **même forme bornée** que le corpus porte 20 ou 6000 documents — les graphes
restent lisibles et légers à toute échelle, **sans rien retirer** (chaque point
est compté). Fonctions pures, déterministes, sans dépendance externe.
"""

from __future__ import annotations

from collections.abc import Sequence


def histogram(values: Sequence[float], n_bins: int) -> list[float]:
    """Comptes par classe de largeur égale sur ``[min, max]`` (``n_bins ≥ 1``).

    Invariant d'échelle : la **forme** ne dépend que de la distribution, pas du
    nombre de points. Toutes valeurs égales → tout dans la première classe
    (largeur nulle, pas de division par zéro)."""
    vals = list(values)
    if not vals or n_bins < 1:
        return []
    lo, hi = min(vals), max(vals)
    if hi <= lo:
        return [float(len(vals))] + [0.0] * (n_bins - 1)
    width = (hi - lo) / n_bins
    counts = [0.0] * n_bins
    for value in vals:
        index = int((value - lo) / width)
        counts[min(index, n_bins - 1)] += 1.0
    return counts


def density_grid(
    points: Sequence[tuple[float, float]], nx: int, ny: int
) -> list[tuple[float, float, float]]:
    """Binning 2D de points ``(x, y)`` ∈ [0,1]² en grille ``nx × ny``.

    Renvoie ``(centre_x, centre_y, compte)`` par cellule **occupée**, trié
    déterministe. Invariant d'échelle : au plus ``nx · ny`` sorties quel que soit
    le nombre de points (un nuage de 6000 points reste lisible et léger)."""
    if nx < 1 or ny < 1:
        return []
    cells: dict[tuple[int, int], int] = {}
    for x, y in points:
        ix = min(nx - 1, max(0, int(max(0.0, min(x, 1.0)) * nx)))
        iy = min(ny - 1, max(0, int(max(0.0, min(y, 1.0)) * ny)))
        cells[(ix, iy)] = cells.get((ix, iy), 0) + 1
    return [
        ((ix + 0.5) / nx, (iy + 0.5) / ny, float(count))
        for (ix, iy), count in sorted(cells.items())
    ]


__all__ = ["density_grid", "histogram"]
