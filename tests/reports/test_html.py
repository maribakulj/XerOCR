"""Helpers de présentation de ``reports.html`` : libellés de vue, i18n minimal."""

from __future__ import annotations

from xerocr.reports.html import localized, view_label


def test_localized_picks_language() -> None:
    assert localized("fr", "Bonjour", "Hello") == "Bonjour"
    assert localized("en", "Bonjour", "Hello") == "Hello"
    assert localized("de", "Bonjour", "Hello") == "Bonjour"  # repli FR


def test_view_label_maps_internal_names_to_human() -> None:
    # le nom interne « text » ne fuit plus dans l'UI
    assert view_label("text", "fr") == "Texte brut"
    assert view_label("text", "en") == "Plain text"
    assert view_label("diplomatic", "fr") == "Transcription diplomatique"
    assert view_label("diplomatic", "en") == "Diplomatic transcription"


def test_view_label_passes_through_already_human_names() -> None:
    # une vue déjà lisible (ex. référence OCR) est rendue telle quelle
    name = "référence OCR (pas une vérité-terrain manuelle)"
    assert view_label(name, "fr") == name
    assert view_label("hipe", "en") == "hipe"


def test_view_label_is_deterministic() -> None:
    assert view_label("text", "fr") == view_label("text", "fr")
