"""Sécurité scientifique : agrégations qui rendent ``None`` sur ensemble vide.

Dette C de l'héritage (ratios/moyennes sur vide → 0 ou division par zéro)
neutralisée dès l'axe texte : une agrégation **sans support** vaut ``None`` (non
applicable), jamais une valeur trompeuse.
"""

from __future__ import annotations

from collections.abc import Sequence


def safe_mean(values: Sequence[float]) -> float | None:
    """Moyenne, ou ``None`` si aucune valeur (support nul)."""
    return sum(values) / len(values) if values else None


# safe_ratio (numérateur/dénominateur) : ajouté avec son 1ᵉʳ consommateur
# (WER/MER, tranche T2) — pas spéculé ici (garde-fou « pas de consommateur ».)


__all__ = ["safe_mean"]
