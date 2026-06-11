"""Helpers SVG **serveur** déterministes pour les graphes du rapport (couche 7).

Aucun JS, aucune lib (≠ Chart.js — cf. ``DECISION_RAPPORT_INTERACTIF.md`` §6) :
du markup SVG inline, **octet-stable**. La **convention d'arrondi** (``num``)
fixe la précision des coordonnées → mêmes octets entre plateformes (pas de
flottant à précision variable). Les couleurs d'accent sont passées par l'appelant
(palette `engine_badges`, jetons de design).
"""

from __future__ import annotations

#: Précision fixe des coordonnées SVG (déterminisme inter-plateformes).
_COORD_DECIMALS = 2


def num(x: float) -> str:
    """Coordonnée SVG arrondie à précision fixe (``num(1/3) == '0.33'``)."""
    return f"{x:.{_COORD_DECIMALS}f}"


def dispersion_strip(
    lo: float,
    med: float,
    mean: float,
    hi: float,
    scale_max: float,
    *,
    accent: str,
    width: float = 280.0,
    height: float = 22.0,
) -> str:
    """Bande de dispersion d'un moteur : axe 0→``scale_max``, segment min→max,
    repère **médiane** (disque) et **moyenne** (tick vertical). Échelle commune
    (``scale_max`` partagé) → bandes comparables entre moteurs."""
    s = scale_max or 1.0

    def x(v: float) -> str:
        return num(max(0.0, min(v, s)) / s * width)

    mid = num(height / 2)
    return (
        f'<svg viewBox="0 0 {num(width)} {num(height)}" class="disp-strip" '
        'preserveAspectRatio="none" aria-hidden="true">'
        f'<line x1="0" y1="{mid}" x2="{num(width)}" y2="{mid}" class="disp-axis"/>'
        f'<line x1="{x(lo)}" y1="{mid}" x2="{x(hi)}" y2="{mid}" class="disp-range" '
        f'style="stroke:{accent}"/>'
        f'<line x1="{x(mean)}" y1="{num(height * 0.18)}" '
        f'x2="{x(mean)}" y2="{num(height * 0.82)}" class="disp-mean"/>'
        f'<circle cx="{x(med)}" cy="{mid}" r="3.5" class="disp-med" '
        f'style="fill:{accent}"/>'
        "</svg>"
    )


__all__ = ["dispersion_strip", "num"]
