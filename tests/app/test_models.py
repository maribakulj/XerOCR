"""Catalogue de modèles par fournisseur : noms + capacité vision, fallback."""

from __future__ import annotations

from xerocr.app.models import ModelInfo, provider_models


def test_known_providers_list_models() -> None:
    for provider in ("openai", "anthropic", "mistral"):
        models = provider_models(provider)
        assert models  # non vide
        assert all(isinstance(m, ModelInfo) for m in models)
        assert all(m.name for m in models)


def test_vision_capability_is_flagged() -> None:
    # gpt-4o* = vision ; un modèle texte-seul (mistral-small) ne l'est pas.
    openai = {m.name: m.vision for m in provider_models("openai")}
    assert openai["gpt-4o"] is True
    mistral = {m.name: m.vision for m in provider_models("mistral")}
    assert mistral["mistral-small-latest"] is False
    assert mistral["pixtral-12b-latest"] is True  # VLM Mistral


def test_unknown_provider_is_empty_not_error() -> None:
    assert provider_models("bogus") == ()
