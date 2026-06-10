"""Diff GT↔hypothèse caractère à caractère : marquage, échappement, déterminisme."""

from __future__ import annotations

from xerocr.reports.text_diff import char_diff


def test_equal_strings_have_no_markup() -> None:
    ref, hyp = char_diff("abcd", "abcd")
    assert ref == "abcd" and hyp == "abcd"
    assert "<del" not in ref and "<ins" not in hyp


def test_substitution_marks_both_sides() -> None:
    # « m » (GT) vs « rn » (hyp) : la confusion OCR classique.
    ref, hyp = char_diff("chemin", "chernin")
    assert ref == 'che<del class="d-del">m</del>in'
    assert hyp == 'che<ins class="d-ins">rn</ins>in'


def test_pure_deletion_only_marks_reference() -> None:
    ref, hyp = char_diff("abc", "ac")  # « b » supprimé
    assert '<del class="d-del">b</del>' in ref
    assert "<ins" not in hyp


def test_pure_insertion_only_marks_hypothesis() -> None:
    ref, hyp = char_diff("ac", "abc")  # « b » inséré
    assert "<del" not in ref
    assert '<ins class="d-ins">b</ins>' in hyp


def test_segments_are_escaped() -> None:
    # Chaque segment est échappé avant marquage (anti-XSS), y compris dans <del>.
    ref, hyp = char_diff("<x>", "y")
    assert "<x>" not in ref
    assert '<del class="d-del">&lt;x&gt;</del>' == ref
    assert '<ins class="d-ins">y</ins>' == hyp


def test_is_deterministic() -> None:
    assert char_diff("Bonjour", "Bnjuor") == char_diff("Bonjour", "Bnjuor")
