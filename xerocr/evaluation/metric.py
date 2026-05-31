"""``DocumentMetric`` + décorateur **pur**.

Une métrique par-document = une fiche (``MetricSpec``, domain) **co-localisée**
avec sa fonction, qui opère sur un ``DocContext``. Le décorateur
``@document_metric`` ne fait que **construire** l'objet — il ne mute aucun
registre global (→ import sans effet de bord, CLAUDE.md §7). La collecte dans un
registre est explicite (``register_default_metrics``).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from xerocr.domain.artifacts import ArtifactType
from xerocr.domain.evaluation import MetricSpec
from xerocr.evaluation.context import DocContext

#: Une métrique par-document calcule un scalaire (ou ``None`` si non applicable).
DocMetricFn = Callable[[DocContext], float | None]


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


__all__ = ["DocMetricFn", "DocumentMetric", "document_metric"]
