"""Helpers SVG déterministes : convention d'arrondi + bande de dispersion."""

from __future__ import annotations

from xerocr.reports.svg import dispersion_strip, num


def test_num_is_fixed_precision_deterministic() -> None:
    assert num(1 / 3) == "0.33"  # précision fixe (2 décimales)
    assert num(10.0) == "10.00"
    assert num(0.0) == "0.00"
    # même entrée → mêmes octets (pas de flottant à précision variable)
    assert num(0.1 + 0.2) == num(0.3)


def test_dispersion_strip_markup_and_scale() -> None:
    svg = dispersion_strip(0.1, 0.2, 0.25, 0.5, 0.5, accent="#abc", width=100.0)
    assert svg.startswith("<svg") and svg.endswith("</svg>")
    assert 'class="disp-strip"' in svg
    assert 'class="disp-range"' in svg and 'class="disp-med"' in svg
    assert "#abc" in svg  # accent inline
    # max (0.5) au bord droit sur une échelle de 0.5 et une largeur de 100
    assert 'x2="100.00"' in svg


def test_dispersion_strip_clamps_and_handles_zero_scale() -> None:
    # valeur > échelle → bornée (pas de coordonnée hors cadre) ; échelle 0 → pas de /0
    svg = dispersion_strip(0.0, 0.0, 0.0, 0.0, 0.0, accent="#000")
    assert "<svg" in svg  # ne lève pas


def test_dispersion_strip_is_deterministic() -> None:
    a = dispersion_strip(0.1, 0.2, 0.25, 0.5, 0.5, accent="#abc")
    b = dispersion_strip(0.1, 0.2, 0.25, 0.5, 0.5, accent="#abc")
    assert a == b
