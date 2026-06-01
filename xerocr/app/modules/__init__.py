"""Registre + factory de modules (couche 6)."""

from __future__ import annotations

from xerocr.app.modules.registry import (
    ModuleRegistry,
    ModuleResolutionError,
    register_default_modules,
)

__all__ = ["ModuleRegistry", "ModuleResolutionError", "register_default_modules"]
