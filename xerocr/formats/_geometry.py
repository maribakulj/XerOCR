"""Primitives géométriques partagées par les formats (points numériques).

Les coordonnées sont des entiers en pixels (convention ALTO et PAGE). On conserve
les valeurs négatives (une région peut déborder la page) ; la réconciliation
d'unités/résolution est une affaire de couche 3.
"""

from __future__ import annotations

Point = tuple[int, int]


def parse_points(raw: str) -> tuple[Point, ...]:
    """Parse une chaîne ``"x1,y1 x2,y2 ..."`` en points entiers.

    Lève ``ValueError`` si un jeton est malformé ; le caller décide d'ignorer
    la géométrie (avec un avertissement) plutôt que de planter.
    """
    points: list[Point] = []
    for token in raw.split():
        x_str, _, y_str = token.partition(",")
        if not _ or not x_str or not y_str:
            raise ValueError(f"point malformé : {token!r}")
        points.append((int(float(x_str)), int(float(y_str))))
    if not points:
        raise ValueError("aucun point")
    return tuple(points)


def format_points(points: tuple[Point, ...]) -> str:
    """Sérialise des points en ``"x1,y1 x2,y2 ..."`` (déterministe)."""
    return " ".join(f"{x},{y}" for x, y in points)
