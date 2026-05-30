"""Sous-couche texte : normalisation de comparaison + lecture de texte brut."""

from __future__ import annotations

from xerocr.formats.text.normalization import (
    DEFAULT_PROFILE,
    NORMALIZATION_PROFILES,
    NormalizationProfile,
    get_builtin_profile,
)
from xerocr.formats.text.plain import read_plaintext

__all__ = [
    "NormalizationProfile",
    "NORMALIZATION_PROFILES",
    "DEFAULT_PROFILE",
    "get_builtin_profile",
    "read_plaintext",
]
