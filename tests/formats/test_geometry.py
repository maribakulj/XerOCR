"""Tests des primitives géométriques partagées."""

from __future__ import annotations

import pytest

from xerocr.formats._geometry import format_points, parse_points


def test_parse_points_valid() -> None:
    assert parse_points("0,0 10,5 10,15") == ((0, 0), (10, 5), (10, 15))


def test_parse_points_truncates_floats() -> None:
    assert parse_points("1.9,2.1") == ((1, 2),)


@pytest.mark.parametrize("bad", ["garbage", "10", "10,", ",5", ""])
def test_parse_points_rejects_malformed(bad: str) -> None:
    with pytest.raises(ValueError):
        parse_points(bad)


def test_format_points_roundtrip() -> None:
    pts = ((0, 0), (10, 5))
    assert parse_points(format_points(pts)) == pts
