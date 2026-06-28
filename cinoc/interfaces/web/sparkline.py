"""Sparkline SVG inline (couche 8) — déterministe, sans JS ni dépendance.

Trace une mini-courbe d'évolution d'une métrique au fil des runs. Rendu
**serveur** (chaîne SVG), donc testable et conforme à l'invariant
anti-hallucination : les points sont une **fonction directe** des valeurs
d'entrée (aucune donnée fabriquée).
"""

from __future__ import annotations

from collections.abc import Sequence


def sparkline_svg(
    values: Sequence[float], *, width: int = 132, height: int = 30
) -> str:
    """Mini-courbe des ``values`` → ``<svg>`` inline. ``""`` si aucune valeur.

    Échelle locale (min..max des valeurs) : on lit la **tendance**, pas la valeur
    absolue (affichée à part). Le dernier point est marqué d'un disque.
    """
    points = [float(v) for v in values if v is not None]
    if not points:
        return ""
    pad = 3.0
    low, high = min(points), max(points)
    span = (high - low) or 1.0
    count = len(points)

    def px(index: int) -> float:
        if count == 1:
            return width / 2
        return pad + (width - 2 * pad) * (index / (count - 1))

    def py(value: float) -> float:
        return pad + (height - 2 * pad) * (1 - (value - low) / span)

    coords = " ".join(f"{px(i):.1f},{py(v):.1f}" for i, v in enumerate(points))
    last_x, last_y = px(count - 1), py(points[-1])
    body = (
        f'<polyline points="{coords}" fill="none" stroke="currentColor" '
        'stroke-width="1.5" stroke-linejoin="round" stroke-linecap="round"/>'
        f'<circle cx="{last_x:.1f}" cy="{last_y:.1f}" r="2.2" fill="currentColor"/>'
    )
    return (
        f'<svg class="spark" viewBox="0 0 {width} {height}" width="{width}" '
        f'height="{height}" preserveAspectRatio="none" aria-hidden="true">'
        f"{body}</svg>"
    )


__all__ = ["sparkline_svg"]
