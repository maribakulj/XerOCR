"""Binning de distributions : histogramme 1D + grille de densité 2D, bornés."""

from __future__ import annotations

from xerocr.reports._binning import density_grid, histogram


def test_histogram_counts_and_edges() -> None:
    assert histogram([], 5) == []
    assert histogram([0.5], 0) == []
    # toutes valeurs égales → première classe (pas de division par zéro)
    assert histogram([0.3, 0.3, 0.3], 4) == [3.0, 0.0, 0.0, 0.0]
    # max dans la dernière classe (borne droite incluse)
    assert histogram([0.0, 0.0, 1.0], 2) == [2.0, 1.0]
    assert sum(histogram([0.1, 0.4, 0.6, 0.9], 4)) == 4.0  # tous comptés


def test_histogram_shape_invariant_to_count() -> None:
    small = histogram([i / 100 for i in range(100)], 10)
    big = histogram([i / 1000 for i in range(1000)], 10)
    assert [round(c / sum(small), 2) for c in small] == [
        round(c / sum(big), 2) for c in big
    ]


def test_density_grid_bins_and_bounds() -> None:
    assert density_grid([], 4, 4) == []
    assert density_grid([(0.1, 0.1)], 0, 4) == []
    cells = density_grid([(0.1, 0.1), (0.12, 0.08)], 4, 4)
    assert len(cells) == 1 and cells[0][2] == 2.0  # même cellule, compte 2
    many = density_grid([(i / 1000, (i * 7 % 1000) / 1000) for i in range(1000)], 8, 8)
    assert len(many) <= 8 * 8  # borné par la grille, pas par le nombre de points


def test_density_grid_is_deterministic() -> None:
    pts = [(0.2, 0.8), (0.9, 0.1), (0.2, 0.81)]
    assert density_grid(pts, 5, 5) == density_grid(pts, 5, 5)
