"""Registre + factory de modules : résolution, validations, rôles LLM."""

from __future__ import annotations

import pytest

from xerocr.app.modules.registry import (
    ModuleRegistry,
    ModuleResolutionError,
    register_default_modules,
)
from xerocr.domain.artifacts import ArtifactType
from xerocr.pipeline.protocols import Module


def _registry() -> ModuleRegistry:
    registry = ModuleRegistry()
    register_default_modules(registry)
    return registry


def test_builds_precomputed_module() -> None:
    module = _registry().build("precomputed:tesseract", {"source_label": "tesseract"})
    assert isinstance(module, Module)
    assert module.name == "precomputed:tesseract"


def test_kinds_listed() -> None:
    assert _registry().kinds() == (
        "alto_assembler",
        "anthropic",
        "azure_di",
        "calamari",
        "google_vision",
        "kraken",
        "mistral",
        "mistral_ocr",
        "ner",
        "ollama",
        "openai",
        "pero",
        "pp_doclayout",
        "precomputed",
        "precomputed_layout",
        "precomputed_region",
        "tesseract",
    )


def test_builds_tesseract_module() -> None:
    module = _registry().build("tesseract:fra", {"label": "fra", "lang": "fra"})
    assert module.name == "tesseract:fra"


def test_builds_pero_and_calamari_modules() -> None:
    pero = _registry().build("pero:c0", {"label": "c0", "model": "config.ini"})
    assert pero.name == "pero:c0"
    assert pero.output_types == frozenset({ArtifactType.RAW_TEXT})
    cal = _registry().build("calamari:c0", {"label": "c0", "model": "ckpt"})
    assert cal.name == "calamari:c0"
    assert cal.output_types == frozenset({ArtifactType.RAW_TEXT})


def test_pero_requires_model() -> None:
    with pytest.raises(ModuleResolutionError):
        _registry().build("pero:c0", {"label": "c0"})


def test_builds_ner_module() -> None:
    module = _registry().build("ner:c0", {"label": "c0", "model": "fr_core_news_sm"})
    assert module.name == "ner:c0"
    assert module.output_types == frozenset({ArtifactType.ENTITIES})
    assert ArtifactType.RAW_TEXT in module.input_types


def test_ner_requires_label() -> None:
    with pytest.raises(ModuleResolutionError):
        _registry().build("ner:c0", {})


def test_builds_azure_di_module() -> None:
    module = _registry().build("azure_di:c0", {"label": "c0", "lang": "fra"})
    assert module.name == "azure_di:c0"
    assert module.input_types == frozenset({ArtifactType.IMAGE})
    assert module.output_types == frozenset({ArtifactType.RAW_TEXT})


def test_builds_google_vision_module() -> None:
    # Le planificateur passe un `lang` à tout moteur OCR : le builder le tolère
    # (Vision détecte la langue, pas de hint) et résout le bon module.
    module = _registry().build("google_vision:c0", {"label": "c0", "lang": "fra"})
    assert module.name == "google_vision:c0"
    assert module.input_types == frozenset({ArtifactType.IMAGE})
    assert module.output_types == frozenset({ArtifactType.RAW_TEXT})


def test_builds_anthropic_with_role() -> None:
    module = _registry().build(
        "anthropic:claude", {"label": "claude", "role": "zero_shot"}
    )
    assert module.name == "anthropic:claude"
    assert module.input_types == frozenset({ArtifactType.IMAGE})
    assert module.output_types == frozenset({ArtifactType.RAW_TEXT})


def test_builds_openai_with_vision_role() -> None:
    module = _registry().build(
        "openai:v", {"label": "v", "role": "text_and_image"}
    )
    assert module.input_types == frozenset(
        {ArtifactType.RAW_TEXT, ArtifactType.IMAGE}
    )


def test_unknown_kind_raises() -> None:
    with pytest.raises(ModuleResolutionError):
        ModuleRegistry().build("mystery:x", {})


def test_missing_source_label_raises() -> None:
    with pytest.raises(ModuleResolutionError):
        _registry().build("precomputed:x", {})


def test_name_mismatch_raises() -> None:
    # nom déclaré "tesseract" mais kwargs construisent "pero" -> incohérence
    with pytest.raises(ModuleResolutionError):
        _registry().build("precomputed:tesseract", {"source_label": "pero"})
