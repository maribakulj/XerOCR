"""Sparkline SVG : déterministe, points = fonction directe des valeurs."""

from __future__ import annotations

from xerocr.interfaces.web.sparkline import sparkline_svg


def test_empty_values_is_empty() -> None:
    assert sparkline_svg([]) == ""


def test_single_value_renders_svg_with_marker() -> None:
    svg = sparkline_svg([0.1])
    assert svg.startswith("<svg")
    assert "<circle" in svg


def test_multiple_values_render_polyline_with_one_point_each() -> None:
    svg = sparkline_svg([0.3, 0.2, 0.1])
    assert "<polyline" in svg
    points = svg.split('points="')[1].split('"')[0]
    assert len(points.split(" ")) == 3  # 3 valeurs → 3 points


def test_deterministic() -> None:
    assert sparkline_svg([0.5, 0.4, 0.42]) == sparkline_svg([0.5, 0.4, 0.42])
