"""Badges moteur A→E : lettre/accent cycliques, ordre stable, cellule sûre."""

from __future__ import annotations

from xerocr.reports.engine_badges import (
    engine_accent,
    engine_cell,
    engine_letter,
    engine_order,
)


def test_letters_are_a_b_c_then_cycle() -> None:
    assert engine_letter(0) == "A"
    assert engine_letter(1) == "B"
    assert engine_letter(4) == "E"
    assert engine_letter(26) == "A"  # cycle A→Z (cas théorique > 26 moteurs)


def test_accents_cycle_over_the_palette() -> None:
    # 5 accents (fern/slate/clay/butter/ink) → l'index 5 retombe sur le 1ᵉʳ.
    assert engine_accent(0) == engine_accent(5)
    assert engine_accent(1) != engine_accent(0)
    assert len({engine_accent(i) for i in range(5)}) == 5  # 5 distincts


def test_order_is_first_appearance_stable() -> None:
    order = engine_order(["tesseract", "openai", "tesseract", "kraken"])
    assert order == {"tesseract": 0, "openai": 1, "kraken": 2}


def test_cell_has_badge_letter_accent_and_escaped_name() -> None:
    cell = engine_cell("tesseract", 0)
    assert 'class="eng-badge"' in cell
    assert ">A</span>" in cell
    assert engine_accent(0) in cell
    assert "tesseract" in cell


def test_cell_escapes_hostile_engine_name() -> None:
    # Le nom du moteur est échappé (pas d'injection HTML via un nom hostile).
    cell = engine_cell("<b>x</b>", 0)
    assert "<b>x</b>" not in cell
    assert "&lt;b&gt;x&lt;/b&gt;" in cell
