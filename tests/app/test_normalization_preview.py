"""Aperçu de normalisation : profil nommé / config YAML custom / erreurs typées."""

from __future__ import annotations

import pytest

from xerocr.app.normalization_preview import (
    NormalizationPreviewError,
    preview_normalization,
)


def test_named_profile_applies() -> None:
    # `caseless` = NFC + casefold → minuscules.
    assert preview_normalization("NOSTRE", profile="caseless") == "nostre"


def test_custom_yaml_config_applies_without_persistence() -> None:
    # Config saisie à la volée : exclut « X » du texte (jamais stockée).
    out = preview_normalization("aXbXc", config='exclude_chars: "X"')
    assert out == "abc"


def test_custom_config_takes_precedence_over_named() -> None:
    out = preview_normalization(
        "aXb", profile="caseless", config='exclude_chars: "X"'
    )
    assert out == "ab"  # la config custom l'emporte


def test_unknown_named_profile_raises() -> None:
    with pytest.raises(NormalizationPreviewError, match="inconnu"):
        preview_normalization("x", profile="nexiste_pas")


def test_invalid_yaml_config_raises() -> None:
    # Clé inconnue → Pydantic (extra interdit) → erreur typée (pas un défaut muet).
    with pytest.raises(NormalizationPreviewError, match="config invalide"):
        preview_normalization("x", config="bogus_key: 1")


def test_neither_profile_nor_config_raises() -> None:
    with pytest.raises(NormalizationPreviewError, match="requis"):
        preview_normalization("x")
