"""Couche 6 — ``app`` : orchestration + registre de modules (coquille mince).

``app`` câble les couches internes et **ne calcule pas** : il appelle pipeline
puis evaluation. ``__init__`` mince, sans effet de bord.
"""

from __future__ import annotations

from cinoc.app.loader import RunSpecError, load_run_spec
from cinoc.app.modules.registry import (
    ModuleRegistry,
    ModuleResolutionError,
    register_default_modules,
)
from cinoc.app.orchestrator import OrchestrationError, run
from cinoc.app.results import RunResultError, dump_run_result, load_run_result
from cinoc.app.security import PathSecurityError, validated_path
from cinoc.app.versioning import resolve_code_version

__all__ = [
    "ModuleRegistry",
    "ModuleResolutionError",
    "OrchestrationError",
    "PathSecurityError",
    "RunResultError",
    "RunSpecError",
    "dump_run_result",
    "load_run_result",
    "load_run_spec",
    "register_default_modules",
    "resolve_code_version",
    "run",
    "validated_path",
]
