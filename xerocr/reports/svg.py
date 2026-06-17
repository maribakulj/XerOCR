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
    "word_overlap_venn",
]


#: Géométrie fixe du Venn à **3** ensembles (le Venn proportionnel à 3 cercles est
#: un problème ouvert) : ``frozenset`` d'indices → (x, y) où inscrire le compte.
_VENN3_POS: dict[frozenset[int], tuple[float, float]] = {
    frozenset({0}): (160.0, 70.0),
    frozenset({1}): (108.0, 158.0),
    frozenset({2}): (212.0, 158.0),
    frozenset({0, 1}): (118.0, 110.0),
    frozenset({0, 2}): (202.0, 110.0),
    frozenset({1, 2}): (160.0, 168.0),
    frozenset({0, 1, 2}): (160.0, 122.0),
}
_VENN3_CIRCLES: tuple[tuple[float, float, float], ...] = (
    (160.0, 100.0, 68.0),
    (122.0, 150.0, 68.0),
    (198.0, 150.0, 68.0),
)


def _venn2_proportional(
    region_counts: dict[frozenset[int], int],
) -> tuple[
    tuple[tuple[float, float, float], ...],
    dict[frozenset[int], tuple[float, float]],
    float,
    float,
]:
    """Géométrie **proportionnelle** d'un Venn à 2 ensembles : rayon ∝ √|ensemble|
    (l'**aire** code l'effectif) et distance des centres ∝ (1 − Jaccard) — fort
    recouvrement → cercles proches, recouvrement nul → cercles tangents.
    Déterministe (les coordonnées sont arrondies à l'écriture par ``num``)."""
    a_only = region_counts.get(frozenset({0}), 0)
    b_only = region_counts.get(frozenset({1}), 0)
    both = region_counts.get(frozenset({0, 1}), 0)
    size_a, size_b = a_only + both, b_only + both
    union = a_only + b_only + both
    width, height, r_max = 320.0, 200.0, 82.0
    cy, center = height / 2, width / 2
    biggest = max(size_a, size_b, 1)
    r_a = max(14.0, r_max * (size_a / biggest) ** 0.5)
    r_b = max(14.0, r_max * (size_b / biggest) ** 0.5)
    # Écart des centres **borné** : ∝ (1 − Jaccard) pour montrer le recouvrement,
    # mais jamais < 0.50·(r_a+r_b) — sinon, quand les deux moteurs ratent presque
    # les mêmes mots (Jaccard ≈ 1), les cercles deviennent concentriques et
    # illisibles. Le **volume** du recouvrement reste lu par le compte central.
    jaccard = both / union if union else 0.0
    gap = (r_a + r_b) * (0.50 + 0.45 * (1.0 - jaccard))
    cx_a, cx_b = center - gap / 2, center + gap / 2
    circles = ((cx_a, cy, r_a), (cx_b, cy, r_b))
    pos = {
        frozenset({0}): (cx_a - r_a * 0.5, cy),
        frozenset({0, 1}): ((cx_a + cx_b) / 2, cy),
        frozenset({1}): (cx_b + r_b * 0.5, cy),
    }
    return circles, pos, width, height


def word_overlap_venn(
    columns: list[str],
    region_counts: dict[frozenset[int], int],
    *,
    accents: list[str],
) -> str:
    """Diagramme de Venn (2 ou 3 moteurs) du **recouvrement** des mots ratés.

    ``columns`` = libellés moteur (lettres) ; ``region_counts`` = ``frozenset``
    d'indices de moteur → nombre de mots ratés par **exactement** cette
    combinaison ; ``accents`` = couleur par moteur (alignée sur ``columns``).
    Cercles teintés (faible opacité) + compte inscrit dans chaque région.
    Au-delà de 3 moteurs un Venn n'est pas lisible → ``""`` (l'appelant garde la
    liste). Compagnon **visuel** (``aria-hidden`` ; la matière vit dans la table).
    Déterministe (coords ``num``), zéro JS."""
    n = len(columns)
    if n == 2:
        circles, pos, width, height = _venn2_proportional(region_counts)
    elif n == 3:
        circles, pos, width, height = _VENN3_CIRCLES, _VENN3_POS, 320.0, 240.0
    else:
        return ""
    parts: list[str] = []
    for i, (cx, cy, r) in enumerate(circles):
        parts.append(
            f'<circle cx="{num(cx)}" cy="{num(cy)}" r="{num(r)}" '
            f'class="venn-circle" style="fill:{accents[i]};stroke:{accents[i]}"/>'
        )
    for i, (cx, _cy, r) in enumerate(circles):
        ly = circles[i][1] - r - 4 if n == 3 and i == 0 else circles[i][1] - r - 4
        parts.append(
            f'<text x="{num(cx)}" y="{num(ly)}" class="venn-label" '
            f'text-anchor="middle">{escape(columns[i])}</text>'
        )
    for region, (x, y) in pos.items():
        count = region_counts.get(region, 0)
        if count <= 0:
            continue
        parts.append(
            f'<text x="{num(x)}" y="{num(y)}" class="venn-count" '
            f'text-anchor="middle">{count}</text>'
        )
    return (
        f'<svg viewBox="0 0 {num(width)} {num(height)}" width="{num(width)}" '
        f'height="{num(height)}" class="venn-svg" aria-hidden="true">'
        f'{"".join(parts)}</svg>'
    )


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
        f'<svg viewBox="0 0 {num(width)} {num(height)}" '
        f'width="{num(width)}" height="{num(height)}" class="wmap-svg" '
        f'aria-hidden="true">{"".join(parts)}</svg>'
    )
