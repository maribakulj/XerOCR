"""Collecteur CER **par ligne et par document** (couche 3).

Mirror de ``LinesCollector`` mais **non poolé** : garde la suite des CER de ligne
de **chaque** (document, pipeline), pour la **heatmap recentrée sur le document**
du détail (rapport). Réutilise l'alignement de lignes (``aligned_line_cers``,
F15) — mêmes lignes que le scoring. ``enabled=False`` (vue dont la normalisation
écrase ``\\n``) → no-op. Déterministe.
"""

from __future__ import annotations

from cinoc.evaluation.analysis import (
    Analysis,
    DocumentLines,
    DocumentLinesPayload,
)
from cinoc.evaluation.lines import aligned_line_cers

#: Plafond de lignes par (doc, pipeline) — borne de sûreté (une page tient dessous).
_MAX_LINES = 400


class DocumentLinesCollector:
    """Accumule les CER de ligne par (document, pipeline) ; ``build`` → payload."""

    def __init__(self, *, enabled: bool = True) -> None:
        self._enabled = enabled
        self._data: dict[str, dict[str, tuple[float, ...]]] = {}

    def observe(
        self, pipeline: str, document_id: str, reference: str, hypothesis: str
    ) -> None:
        if not self._enabled:
            return
        cers = aligned_line_cers(reference, hypothesis)
        if not cers:
            return
        self._data.setdefault(document_id, {})[pipeline] = tuple(cers[:_MAX_LINES])

    def build(self, view: str) -> Analysis | None:
        """Payload CER de ligne par document (ordre déterministe), ``None`` si vide."""
        if not self._data:
            return None
        documents = tuple(
            DocumentLines(
                document_id=doc,
                pipelines=tuple(sorted(self._data[doc].items())),
            )
            for doc in sorted(self._data)
        )
        return Analysis(
            scope="corpus", view=view, payload=DocumentLinesPayload(documents=documents)
        )


__all__ = ["DocumentLinesCollector"]
