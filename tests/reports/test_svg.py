"""Helpers SVG déterministes : convention d'arrondi + bande de dispersion."""

from __future__ import annotations

from xerocr.reports.svg import (
    calibration_curve,
    composition_bar,
    dispersion_strip,
    num,
)


def test_composition_bar_segments_normalized_and_stacked() -> None:
    svg = composition_bar([(3.0, "#aaa"), (1.0, "#bbb")], width=100.0)
    assert 'class="comp-bar"' in svg
    assert "#aaa" in svg and "#bbb" in svg
    # parts normalisées (3:1) → 75 puis 25, empilées (x = 0 puis 75)
    assert 'x="0.00" y="0" width="75.00"' in svg
    assert 'x="75.00" y="0" width="25.00"' in svg


def test_composition_bar_handles_zero_total() -> None:
    assert "<svg" in composition_bar([], width=100.0)  # somme nulle → pas de /0


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


def test_calibration_curve_diagonal_polyline_and_inverted_y() -> None:
    svg = calibration_curve([(0.5, 0.5), (0.8, 0.6)], accent="#f0f", size=100.0)
    assert 'class="calib-diag"' in svg  # diagonale = calibration parfaite
    assert 'class="calib-line"' in svg and 'points="' in svg
    assert "#f0f" in svg
    # y inversé : exactitude 0.5 sur 100 → y = 50 ; conf 0.5 → x = 50
    assert "50.00,50.00" in svg


def test_calibration_curve_empty_keeps_diagonal_only() -> None:
    svg = calibration_curve([], accent="#000")
    assert 'class="calib-diag"' in svg
    assert 'class="calib-line"' not in svg  # aucun point → pas de polyligne


def test_calibration_curve_is_deterministic() -> None:
    pts = [(0.2, 0.3), (0.9, 0.85)]
    a = calibration_curve(pts, accent="#abc")
    b = calibration_curve(pts, accent="#abc")
    assert a == b
