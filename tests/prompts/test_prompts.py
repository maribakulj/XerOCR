"""Catalogue de prompts curés : lecture dynamique, placeholder, erreurs."""

from __future__ import annotations

import pytest

from xerocr.prompts import PromptError, available_prompts, load_prompt


def test_sixteen_prompts_available_and_sorted() -> None:
    names = available_prompts()
    assert len(names) == 16  # 13 correction + 3 zero-shot (portés de Picarones)
    assert list(names) == sorted(names)
    assert "correction_medieval_french" in names
    assert "zero_shot_medieval_french" in names


def test_correction_prompts_use_ocr_text_placeholder() -> None:
    # Les prompts de correction injectent le texte OCR via {ocr_text} (convention
    # XerOCR, ≠ {ocr_output} de Picarones) ; sinon l'OCR ne serait jamais inséré.
    for name in available_prompts():
        text = load_prompt(name)
        assert text  # jamais vide
        if name.startswith("correction_"):
            assert "{ocr_text}" in text, name
        else:  # zero_shot_* : image → texte, aucun placeholder
            assert "{ocr_text}" not in text, name


def test_unknown_prompt_raises_not_silent() -> None:
    with pytest.raises(PromptError, match="inconnu"):
        load_prompt("nexiste_pas")


def test_no_stale_picarones_references() -> None:
    # Donnée portée et nettoyée (CLAUDE §8 : aucun marqueur Picarones/sprint).
    for name in available_prompts():
        lowered = load_prompt(name).lower()
        assert "picarones" not in lowered
