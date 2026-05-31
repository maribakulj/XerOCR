"""Couche 6 — ``app`` : orchestration + registre de modules (coquille mince).

``app`` câble les couches internes et **ne calcule pas** : il appelle pipeline
puis evaluation. ``__init__`` mince, sans effet de bord.
"""

from __future__ import annotations

from xerocr.app.modules.registry import (
    ModuleRegistry,
    ModuleResolutionError,
    register_default_modules,
)
from xerocr.app.orchestrator import OrchestrationError, run

__all__ = [
    "ModuleRegistry",
    "ModuleResolutionError",
    "OrchestrationError",
    "register_default_modules",
    "run",
]
