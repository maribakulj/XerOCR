"""Couche 3 — ``evaluation`` : métriques, registre type-driven, runner, RunResult.

``__init__`` mince, sans effet de bord : le registre ne s'auto-peuple pas
(``register_default_metrics`` est explicite).
"""

from __future__ import annotations

from xerocr.evaluation.context import DocContext
from xerocr.evaluation.errors import EvaluationError
from xerocr.evaluation.metric import DocumentMetric, document_metric
from xerocr.evaluation.registry import MetricRegistry, register_default_metrics
from xerocr.evaluation.result import (
    MetricScore,
    PipelineResult,
    RunDocumentResult,
    RunResult,
)
from xerocr.evaluation.runner import PipelineOutputs, evaluate_run

__all__ = [
    "DocContext",
    "DocumentMetric",
    "EvaluationError",
    "MetricRegistry",
    "MetricScore",
    "PipelineOutputs",
    "PipelineResult",
    "RunDocumentResult",
    "RunResult",
    "document_metric",
    "evaluate_run",
    "register_default_metrics",
]
