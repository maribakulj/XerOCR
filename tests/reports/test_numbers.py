"""Formatage localisé des nombres affichés : virgule (fr) vs point (en)."""

from __future__ import annotations

from cinoc.reports._numbers import fmt, fmt_pct, localize_decimal


def test_localize_decimal_swaps_only_in_french() -> None:
    assert localize_decimal("12.3 %", "fr") == "12,3 %"
    assert localize_decimal("12.3 %", "en") == "12.3 %"
    assert localize_decimal("12.3 %", "de") == "12.3 %"  # repli = point (non-fr)


def test_localize_decimal_noop_without_dot() -> None:
    assert localize_decimal("1200", "fr") == "1200"  # entier : pas de groupement


def test_fmt_applies_spec_then_localizes() -> None:
    assert fmt(1 / 3, "fr", ".2f") == "0,33"
    assert fmt(1 / 3, "en", ".2f") == "0.33"
    assert fmt(2.0, "fr", ".3f") == "2,000"


def test_fmt_pct_scales_and_localizes() -> None:
    assert fmt_pct(0.123, "fr") == "12,3 %"
    assert fmt_pct(0.123, "en") == "12.3 %"
    assert fmt_pct(0.5, "fr", decimals=0) == "50 %"


def test_fmt_pct_without_scale() -> None:
    assert fmt_pct(42.0, "fr", scale=False) == "42,0 %"
    assert fmt_pct(42.0, "en", scale=False) == "42.0 %"
