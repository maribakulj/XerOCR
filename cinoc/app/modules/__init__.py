"""Registre + factory de modules (couche 6)."""

from __future__ import annotations

from cinoc.app.modules.discovery import ENTRY_POINT_GROUP, discover_plugins
from cinoc.app.modules.registry import (
    ModuleRegistry,
    ModuleResolutionError,
    register_default_modules,
)

__all__ = [
    "ENTRY_POINT_GROUP",
    "ModuleRegistry",
    "ModuleResolutionError",
    "discover_plugins",
    "register_default_modules",
]
