"""Taxonomie d'erreurs **par document** (couche 3).

Mirror **non-poolé** de ``TaxonomyCollector`` : classe les erreurs (mêmes règles
pures ``classify_texts``) par **(document, pipeline)** → ``DocumentTaxonomyPayload``,
qui alimente le **profil d'erreurs recentré sur le doc** du détail (rapport).
Déterministe.
"""

from __future__ import annotations

from collections import Counter

from xerocr.evaluation.analysis import (
    Analysis,
    DocumentTaxonomy,
    DocumentTaxonomyPayload,
    PipelineTaxonomy,
    TaxonomyCount,
)
from xerocr.evaluation.taxonomy import CLASSES, classify_texts


class DocumentTaxonomyCollector:
    """Accumule les classes d'erreurs par (document, pipeline) ; ``build`` → payload."""

    def __init__(self) -> None:
        self._counts: dict[str, dict[str, Counter[str]]] = {}

    def observe(
        self, pipeline: str, document_id: str, reference: str, hypothesis: str
    ) -> None:
        bucket = self._counts.setdefault(document_id, {}).setdefault(
            pipeline, Counter()
        )
        bucket.update(classify_texts(reference, hypothesis))

    def build(self, view: str) -> Analysis | None:
        """Payload du profil d'erreurs par document (ordre déterministe)."""
        documents: list[DocumentTaxonomy] = []
        for doc in sorted(self._counts):
            pipelines: list[PipelineTaxonomy] = []
            for pipeline, bucket in sorted(self._counts[doc].items()):
                total = sum(bucket.values())
                if total == 0:
                    continue
                counts = tuple(
                    TaxonomyCount(label=cls, count=bucket[cls])
                    for cls in CLASSES
                    if bucket[cls] > 0
                )
                pipelines.append(
                    PipelineTaxonomy(
                        pipeline=pipeline, total_errors=total, counts=counts
                    )
                )
            if pipelines:
                documents.append(
                    DocumentTaxonomy(document_id=doc, pipelines=tuple(pipelines))
                )
        if not documents:
            return None
        return Analysis(
            scope="corpus",
            view=view,
            payload=DocumentTaxonomyPayload(
                classes=CLASSES, documents=tuple(documents)
            ),
        )


__all__ = ["DocumentTaxonomyCollector"]
