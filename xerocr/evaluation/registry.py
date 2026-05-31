"""Registre de métriques **type-driven** (sélection par ``input_types``).

Unique (les systèmes parallèles de l'héritage sont abandonnés) et
**instanciable** : il ne s'auto-peuple pas à l'import — ``register_default_metrics``
est appelé **explicitement** par l'app (CLAUDE.md §7, import sans effet de bord).
"""

from __future__ import annotations

from xerocr.domain.artifacts import ArtifactType
from xerocr.evaluation.metric import DocumentMetric


class MetricRegistry:
    """Associe des noms de métriques à leurs fiches + fonctions."""

    def __init__(self) -> None:
        self._document: dict[str, DocumentMetric] = {}

    def register_document_metric(self, metric: DocumentMetric) -> None:
        """Enregistre (ou remplace) une métrique par-document. Idempotent."""
        self._document[metric.name] = metric

    def document_metric(self, name: str) -> DocumentMetric | None:
        return self._document.get(name)

    def for_input_types(
        self, reference: ArtifactType, hypothesis: ArtifactType
    ) -> tuple[DocumentMetric, ...]:
        """Métriques par-document applicables à la signature ``(ref, hyp)``."""
        return tuple(
            metric
            for metric in self._document.values()
            if metric.input_types == (reference, hypothesis)
        )

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._document))


def register_default_metrics(registry: MetricRegistry) -> None:
    """Collecte explicite du socle de métriques (aucun effet de bord à l'import)."""
    from xerocr.evaluation.metrics.text import TEXT_METRICS

    for metric in TEXT_METRICS:
        registry.register_document_metric(metric)


__all__ = ["MetricRegistry", "register_default_metrics"]
