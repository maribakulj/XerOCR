"""Métriques co-localisées (fiche + fonction) + décorateurs **purs**.

- ``DocumentMetric`` (par-document) : opère sur un ``DocContext``.
- ``CrossEngineMetric`` (inter-moteurs) : opère sur un ``CrossEngineContext`` et
  renvoie ``(valeur, support)``.

Les décorateurs **construisent** l'objet sans muter de registre global (→ import
sans effet de bord, CLAUDE.md §7) ; la collecte est explicite.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from xerocr.domain.artifacts import ArtifactType
from xerocr.domain.evaluation import MetricSpec
from xerocr.evaluation.context import CrossEngineContext, DocContext

#: Une métrique par-document calcule un scalaire (ou ``None`` si non applicable).
DocMetricFn = Callable[[DocContext], float | None]

#: Une métrique inter-moteurs renvoie ``(valeur, support)`` (``None`` si N/A).
CrossEngineFn = Callable[[CrossEngineContext], tuple[float | None, int]]


@dataclass(frozen=True)
class DocumentMetric:
    """Métrique scalaire par-document : fiche + fonction co-localisées."""

    spec: MetricSpec
    fn: DocMetricFn

    @property
    def name(self) -> str:
        return self.spec.name

    @property
    def input_types(self) -> tuple[ArtifactType, ArtifactType]:
        return self.spec.input_types


@dataclass(frozen=True)
class CrossEngineMetric:
    """Métrique inter-moteurs : compare les pipelines entre eux sur une métrique."""

    name: str
    description: str
    fn: CrossEngineFn


def document_metric(
    *,
    name: str,
    input_types: tuple[ArtifactType, ArtifactType],
    description: str = "",
    higher_is_better: bool = False,
    tags: frozenset[str] = frozenset(),
) -> Callable[[DocMetricFn], DocumentMetric]:
    """Construit une ``DocumentMetric`` depuis une fonction (pur, sans effet)."""

    def decorate(fn: DocMetricFn) -> DocumentMetric:
        return DocumentMetric(
            spec=MetricSpec(
                name=name,
                input_types=input_types,
                description=description,
                higher_is_better=higher_is_better,
                tags=tags,
            ),
            fn=fn,
        )

    return decorate


def cross_engine_metric(
    *, name: str, description: str = ""
) -> Callable[[CrossEngineFn], CrossEngineMetric]:
    """Construit une ``CrossEngineMetric`` depuis une fonction (pur, sans effet)."""

    def decorate(fn: CrossEngineFn) -> CrossEngineMetric:
        return CrossEngineMetric(name=name, description=description, fn=fn)

    return decorate


__all__ = [
    "CrossEngineFn",
    "CrossEngineMetric",
    "DocMetricFn",
    "DocumentMetric",
    "cross_engine_metric",
    "document_metric",
]
