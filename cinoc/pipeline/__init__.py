"""Couche 4 — ``pipeline`` : contrat d'exécution des modules + exécuteur.

Expose le ``Module`` Protocol (point d'extension unique), le contexte/contrôle
d'exécution et l'exécuteur mono-document. ``__init__`` mince, sans effet de bord.
"""

from __future__ import annotations

from cinoc.pipeline.executor import PipelineExecutor, PipelineStepError
from cinoc.pipeline.protocols import Module, ParamValue
from cinoc.pipeline.run_control import RunControl
from cinoc.pipeline.types import RunContext

__all__ = [
    "Module",
    "ParamValue",
    "PipelineExecutor",
    "PipelineStepError",
    "RunContext",
    "RunControl",
]
