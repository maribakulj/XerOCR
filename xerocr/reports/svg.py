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


__all__ = ["calibration_curve", "dispersion_strip", "num"]


def calibration_curve(
    points: list[tuple[float, float]],
    *,
    accent: str,
    size: float = 180.0,
) -> str:
    """Courbe de fiabilité : ``points`` = ``(confiance, exactitude)`` dans [0,1].

    Diagonale pointillée = calibration parfaite ; la polyligne (+ disques) = le
    moteur. L'axe **y** est inversé (SVG vers le bas) : ``y = (1 - exactitude)``.
    Déterministe (coordonnées via ``num``), zéro JS."""

    def px(v: float) -> float:
        return max(0.0, min(v, 1.0)) * size

    diag = (
        f'<line x1="0" y1="{num(size)}" x2="{num(size)}" y2="0" class="calib-diag"/>'
    )
    if not points:
        return (
            f'<svg viewBox="0 0 {num(size)} {num(size)}" class="calib-svg" '
            f'aria-hidden="true">{diag}</svg>'
        )
    pts = sorted(points)
    coords = " ".join(f"{num(px(c))},{num(size - px(a))}" for c, a in pts)
    dots = "".join(
        f'<circle cx="{num(px(c))}" cy="{num(size - px(a))}" r="2.6" '
        f'class="calib-pt" style="fill:{accent}"/>'
        for c, a in pts
    )
    return (
        f'<svg viewBox="0 0 {num(size)} {num(size)}" class="calib-svg" '
        f'aria-hidden="true">{diag}'
        f'<polyline points="{coords}" class="calib-line" style="stroke:{accent}"/>'
        f"{dots}</svg>"
    )
