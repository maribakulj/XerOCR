"""Registre de métriques **par-document** (type-driven) + **inter-moteurs**.

Unique et **instanciable** : il ne s'auto-peuple pas à l'import —
``register_default_metrics`` est appelé **explicitement** par l'app (CLAUDE.md §7).
"""

from __future__ import annotations

from xerocr.domain.artifacts import ArtifactType
from xerocr.evaluation.metric import CrossEngineMetric, DocumentMetric


class MetricRegistry:
    """Associe des noms (par-doc et inter-moteurs) à leurs fiches + fonctions."""

    def __init__(self) -> None:
        self._document: dict[str, DocumentMetric] = {}
        self._cross_engine: dict[str, CrossEngineMetric] = {}

    def register_document_metric(self, metric: DocumentMetric) -> None:
        """Enregistre (ou remplace) une métrique par-document. Idempotent."""
        self._document[metric.name] = metric

    def register_cross_engine_metric(self, metric: CrossEngineMetric) -> None:
        """Enregistre (ou remplace) une métrique inter-moteurs. Idempotent."""
        self._cross_engine[metric.name] = metric

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

    def cross_engine_metrics(self) -> tuple[CrossEngineMetric, ...]:
        """Métriques inter-moteurs enregistrées, triées par nom (déterministe)."""
        return tuple(self._cross_engine[name] for name in sorted(self._cross_engine))

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._document))


def register_default_metrics(registry: MetricRegistry) -> None:
    """Collecte explicite du socle de métriques (aucun effet de bord à l'import)."""
    from xerocr.evaluation.metrics.diacritics import DIACRITIC_METRICS
    from xerocr.evaluation.metrics.layout import LAYOUT_METRICS
    from xerocr.evaluation.metrics.stats import CROSS_ENGINE_METRICS
    from xerocr.evaluation.metrics.text import TEXT_METRICS

    for document in (*TEXT_METRICS, *DIACRITIC_METRICS, *LAYOUT_METRICS):
        registry.register_document_metric(document)
    for cross in CROSS_ENGINE_METRICS:
        registry.register_cross_engine_metric(cross)


__all__ = ["MetricRegistry", "register_default_metrics"]
