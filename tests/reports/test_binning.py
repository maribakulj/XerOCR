"""Binning de distributions : histogramme 1D borné, invariant d'échelle."""

from __future__ import annotations

from xerocr.reports._binning import histogram


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
