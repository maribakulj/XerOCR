"""Helpers SVG **serveur** déterministes pour les graphes du rapport (couche 7).

Aucun JS, aucune lib (≠ Chart.js — cf. ``DECISION_RAPPORT_INTERACTIF.md`` §6) :
du markup SVG inline, **octet-stable**. La **convention d'arrondi** (``num``)
fixe la précision des coordonnées → mêmes octets entre plateformes (pas de
flottant à précision variable). Les couleurs d'accent sont passées par l'appelant
(palette `engine_badges`, jetons de design).
"""

from __future__ import annotations

from xerocr.reports.html import escape

#: Précision fixe des coordonnées SVG (déterminisme inter-plateformes).
_COORD_DECIMALS = 2

#: Mots tronqués à l'affichage dans la heatmap (le mot complet vit dans le payload
#: et la table de la section) — garde les libellés dans la gouttière de gauche.
_HEATMAP_WORD_CHARS = 22


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


__all__ = [
    "bar_series",
    "calibration_curve",
    "composition_bar",
    "dispersion_strip",
    "num",
    "word_engine_heatmap",
]


def bar_series(
    values: list[float],
    *,
    accent: str,
    width: float = 320.0,
    height: float = 120.0,
    gap: float = 2.0,
) -> str:
    """Barres verticales (``values`` dans l'ordre fourni — l'appelant trie).

    Hauteur ∝ valeur / max ; échelle propre à la série. Étiré par CSS
    (``preserveAspectRatio="none"``). Déterministe (coords ``num``), zéro JS."""
    n = len(values)
    if n == 0:
        return (
            f'<svg viewBox="0 0 {num(width)} {num(height)}" class="bars-svg" '
            'aria-hidden="true"></svg>'
        )
    vmax = max(values) or 1.0
    bw = (width - gap * (n - 1)) / n
    bars: list[str] = []
    x = 0.0
    for v in values:
        h = max(0.0, v) / vmax * height
        bars.append(
            f'<rect x="{num(x)}" y="{num(height - h)}" width="{num(bw)}" '
            f'height="{num(h)}" style="fill:{accent}"/>'
        )
        x += bw + gap
    return (
        f'<svg viewBox="0 0 {num(width)} {num(height)}" class="bars-svg" '
        f'preserveAspectRatio="none" aria-hidden="true">{"".join(bars)}</svg>'
    )


def composition_bar(
    segments: list[tuple[float, str]],
    *,
    width: float = 100.0,
    height: float = 14.0,
) -> str:
    """Barre **empilée** horizontale : ``segments`` = ``(part, couleur)``.

    Les parts sont normalisées (somme → largeur pleine). Étirée à 100 % par CSS
    (``preserveAspectRatio="none"``). Déterministe (coords ``num``), zéro JS."""
    total = sum(s for s, _ in segments) or 1.0
    parts: list[str] = []
    x = 0.0
    for share, color in segments:
        w = share / total * width
        parts.append(
            f'<rect x="{num(x)}" y="0" width="{num(w)}" height="{num(height)}" '
            f'style="fill:{color}"/>'
        )
        x += w
    return (
        f'<svg viewBox="0 0 {num(width)} {num(height)}" class="comp-bar" '
        f'preserveAspectRatio="none" aria-hidden="true">{"".join(parts)}</svg>'
    )


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


def _clip_word(word: str) -> str:
    """Tronque un mot à l'affichage (le mot complet reste dans la table HTML)."""
    if len(word) <= _HEATMAP_WORD_CHARS:
        return word
    return word[: _HEATMAP_WORD_CHARS - 1] + "…"


def word_engine_heatmap(
    columns: list[str],
    rows: list[tuple[str, list[int]]],
    *,
    accent: str,
    cell_w: float = 30.0,
    cell_h: float = 22.0,
    label_w: float = 156.0,
    header_h: float = 18.0,
) -> str:
    """Heatmap mots × moteurs : lignes = mots **verbatim**, colonnes = moteurs.

    ``columns`` = libellés de colonnes (lettres moteur) ; ``rows`` =
    ``(mot, [compte par colonne])`` aligné sur ``columns``. Chaque case est teintée
    par **opacité ∝ compte / max** (case vide = pas de fond), le compte est inscrit ;
    le mot (tronqué à l'affichage) et les en-têtes sont **échappés** (texte SVG sûr,
    anti-XSS). Compagnon **visuel** de la table de la section (``aria-hidden`` : la
    matière accessible vit dans la table). Déterministe (coords ``num``),
    octet-stable, zéro JS."""
    n_cols = len(columns)
    width = label_w + cell_w * n_cols
    height = header_h + cell_h * len(rows)
    vmax = max((max(counts, default=0) for _, counts in rows), default=0) or 1
    parts: list[str] = []
    for j, column in enumerate(columns):
        cx = label_w + cell_w * j + cell_w / 2
        parts.append(
            f'<text x="{num(cx)}" y="{num(header_h - 5)}" class="wmap-head" '
            f'text-anchor="middle">{escape(column)}</text>'
        )
    for i, (word, counts) in enumerate(rows):
        y = header_h + cell_h * i
        ty = y + cell_h / 2 + 3.5
        parts.append(
            f'<text x="{num(label_w - 7)}" y="{num(ty)}" class="wmap-word" '
            f'text-anchor="end">{escape(_clip_word(word))}</text>'
        )
        for j in range(n_cols):
            count = counts[j] if j < len(counts) else 0
            x = label_w + cell_w * j
            if count <= 0:
                parts.append(
                    f'<rect x="{num(x)}" y="{num(y)}" width="{num(cell_w)}" '
                    f'height="{num(cell_h)}" class="wmap-cell" style="fill:none"/>'
                )
                continue
            opacity = 0.18 + 0.82 * count / vmax
            ink = "var(--paper)" if opacity > 0.55 else "var(--ink)"
            parts.append(
                f'<rect x="{num(x)}" y="{num(y)}" width="{num(cell_w)}" '
                f'height="{num(cell_h)}" class="wmap-cell" '
                f'style="fill:{accent};opacity:{num(opacity)}"/>'
                f'<text x="{num(x + cell_w / 2)}" y="{num(ty)}" class="wmap-count" '
                f'text-anchor="middle" style="fill:{ink}">{count}</text>'
            )
    return (
        f'<svg viewBox="0 0 {num(width)} {num(height)}" class="wmap-svg" '
        f'aria-hidden="true">{"".join(parts)}</svg>'
    )
