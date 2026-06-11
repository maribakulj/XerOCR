"""Catalogue de **prompts curés par période** (DONNÉE, ≠ surface exécutable).

16 prompts ``.txt`` empaquetés — **correction** (texte OCR → corrigé, placeholder
``{ocr_text}``, modes ``text_only``/``text_and_image``) et **zero-shot** (image →
texte, sans placeholder, mode ``zero_shot``), par type de document et langue
(médiéval FR/EN, imprimé ancien, presse XIXe FR/EN/DE/européenne).

Lus **dynamiquement** du paquet (jamais une liste statique — la leçon des profils
de normalisation). La sélection (par nom) est résolue **au plan**
(``app.run_planning``) → passée comme ``prompt`` à l'adapter LLM/VLM ; un **prompt
libre** saisi par l'utilisateur reste prioritaire.
"""

from __future__ import annotations

from importlib import resources

from xerocr.domain.errors import XerOCRError

_SUFFIX = ".txt"


class PromptError(XerOCRError):
    """Nom de prompt curé inconnu (jamais un défaut muet)."""


def _names() -> list[str]:
    """Noms (sans extension) des prompts ``.txt`` du paquet, triés."""
    return sorted(
        entry.name[: -len(_SUFFIX)]
        for entry in resources.files(__name__).iterdir()
        if entry.name.endswith(_SUFFIX)
    )


def available_prompts() -> tuple[str, ...]:
    """Noms des prompts curés disponibles (reflètent le paquet, pas une liste figée)."""
    return tuple(_names())


def load_prompt(name: str) -> str:
    """Texte du prompt curé ``name`` ; ``PromptError`` si inconnu."""
    if name not in _names():
        raise PromptError(f"prompt curé inconnu : {name!r}.")
    return (
        resources.files(__name__)
        .joinpath(f"{name}{_SUFFIX}")
        .read_text(encoding="utf-8")
        .strip()
    )


__all__ = ["PromptError", "available_prompts", "load_prompt"]
