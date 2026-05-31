"""Registre + factory de modules : résolution, validations."""

from __future__ import annotations

import pytest

from xerocr.app.modules.registry import (
    ModuleRegistry,
    ModuleResolutionError,
    register_default_modules,
)
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
    assert _registry().kinds() == ("ollama", "openai", "precomputed", "tesseract")


def test_builds_tesseract_module() -> None:
    module = _registry().build("tesseract:fra", {"label": "fra", "lang": "fra"})
    assert module.name == "tesseract:fra"


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
