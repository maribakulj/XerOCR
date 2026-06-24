"""Binning de distributions pour les graphes du rapport (couche 7).

Agréger plutôt qu'énumérer : un histogramme a la **même forme bornée** que le
corpus porte 20 ou 6000 documents — les graphes restent lisibles et légers à
toute échelle, **sans rien retirer** (chaque point est compté). Fonctions pures,
déterministes, sans dépendance externe.
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


__all__ = ["histogram"]
