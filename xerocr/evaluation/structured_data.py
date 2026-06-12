"""Collecteur de **données structurées** par pipeline (couche 3).

Pattern ``TaxonomyCollector`` : observe (pipeline, GT, hypothèse) au fil du
scoring — mêmes représentations normalisées, zéro relecture — puis ``build``
agrège par catégorie (micro : Σ comptes) → ``StructuredDataPayload``.
Adaptatif : GT du corpus sans séquence → ``None`` (pas de payload vide).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from xerocr.evaluation.analysis import (
    Analysis,
    CategoryBreakdown,
    PipelineStructuredData,
    StructuredDataPayload,
)
from xerocr.evaluation.metrics.structured_data import CATEGORIES, sequence_counts

#: Plafond de formes perdues embarquées, par (pipeline × catégorie).
_MAX_LOST_SAMPLES = 12


@dataclass
class _Slot:
    """Sommes courantes d'une (pipeline × catégorie)."""

    n_total: int = 0
    n_strict: int = 0
    n_value: int = 0
    lost: list[str] = field(default_factory=list)


class StructuredDataCollector:
    """Accumule les comptes par (pipeline × catégorie), ``build`` borne."""

    def __init__(self) -> None:
        self._sums: dict[str, dict[str, _Slot]] = {}
        self._pipelines: list[str] = []

    def observe(self, pipeline: str, reference: str, hypothesis: str) -> None:
        for category, counts in sequence_counts(reference, hypothesis).items():
            if pipeline not in self._sums:
                self._sums[pipeline] = {}
                self._pipelines.append(pipeline)
            slot = self._sums[pipeline].setdefault(category, _Slot())
            slot.n_total += counts.n_total
            slot.n_strict += counts.n_strict
            slot.n_value += counts.n_value
            missing = _MAX_LOST_SAMPLES - len(slot.lost)
            if missing > 0:
                slot.lost.extend(counts.lost[:missing])

    def build(self, view: str) -> Analysis | None:
        """Payload de la vue, ``None`` si aucune séquence dans la GT."""
        rows: list[PipelineStructuredData] = []
        for pipeline in self._pipelines:
            categories = tuple(
                CategoryBreakdown(
                    category=category,
                    n_total=slot.n_total,
                    n_strict=slot.n_strict,
                    n_value=slot.n_value,
                    strict_score=slot.n_strict / slot.n_total,
                    value_score=slot.n_value / slot.n_total,
                    lost=tuple(slot.lost),
                )
                for category in CATEGORIES
                if (slot := self._sums[pipeline].get(category)) is not None
            )
            if categories:
                rows.append(
                    PipelineStructuredData(pipeline=pipeline, categories=categories)
                )
        if not rows:
            return None
        return Analysis(
            scope="corpus",
            view=view,
            payload=StructuredDataPayload(pipelines=tuple(rows)),
        )


__all__ = ["StructuredDataCollector"]
