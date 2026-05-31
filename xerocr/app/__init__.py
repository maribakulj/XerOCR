"""Couche 6 — ``app`` : orchestration + registre de modules (coquille mince).

``app`` câble les couches internes et **ne calcule pas** : il appelle pipeline
puis evaluation. ``__init__`` mince, sans effet de bord.
"""

from __future__ import annotations

from xerocr.app.loader import RunSpecError, load_run_spec
from xerocr.app.modules.registry import (
    ModuleRegistry,
    ModuleResolutionError,
    register_default_modules,
)
from xerocr.app.orchestrator import OrchestrationError, run
from xerocr.app.security import PathSecurityError, validated_path

__all__ = [
    "ModuleRegistry",
    "ModuleResolutionError",
    "OrchestrationError",
    "PathSecurityError",
    "RunSpecError",
    "load_run_spec",
    "register_default_modules",
    "run",
    "validated_path",
]
