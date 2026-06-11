"""Collecteur de **textes complets** des pires documents (couche 3).

Mirror de ``DiagnosticsCollector`` : observe (pipeline, doc, ref, hyp, CER) par
document scoré, puis ``build`` ne garde que les **top-N pires** documents (par CER
moyen) avec leurs textes **tronqués** → ``DocumentTextsPayload`` borné, qui
alimente le **diff pleine page** du détail document (rapport). Déterministe.
"""

from __future__ import annotations

from statistics import fmean

from xerocr.evaluation.analysis import (
    Analysis,
    DocumentTexts,
    DocumentTextsPayload,
)

#: Plafond de documents dont on embarque les textes (top-N pires par CER).
_TOP_DOCUMENTS = 20
#: Plafond de caractères par texte (aligné sur ``analysis._MAX_TEXT_CHARS``).
_MAX_CHARS = 8000


class DocumentTextsCollector:
    """Accumule les textes par document, ``build`` borne aux pires (CER moyen)."""

    def __init__(self) -> None:
        self._reference: dict[str, str] = {}
        self._hyps: dict[str, dict[str, str]] = {}
        self._cers: dict[str, list[float]] = {}

    def observe(
        self,
        pipeline: str,
        document_id: str,
        reference: str,
        hypothesis: str,
        cer: float | None,
    ) -> None:
        self._reference.setdefault(document_id, reference[:_MAX_CHARS])
        self._hyps.setdefault(document_id, {})[pipeline] = hypothesis[:_MAX_CHARS]
        if cer is not None:
            self._cers.setdefault(document_id, []).append(cer)

    def build(self, view: str) -> Analysis | None:
        """Payload des **top-N pires** documents (CER moyen ↓), ``None`` si rien."""
        if not self._reference:
            return None

        def _mean_cer(doc: str) -> float:
            values = self._cers.get(doc)
            return fmean(values) if values else 0.0

        ranked = sorted(self._reference, key=lambda d: (-_mean_cer(d), d))[
            :_TOP_DOCUMENTS
        ]
        documents = tuple(
            DocumentTexts(
                document_id=doc,
                reference=self._reference[doc],
                # Hypothèses ordonnées (pipeline) — déterministe.
                hypotheses=tuple(sorted(self._hyps.get(doc, {}).items())),
            )
            for doc in ranked
        )
        return Analysis(
            scope="corpus", view=view, payload=DocumentTextsPayload(documents=documents)
        )


__all__ = ["DocumentTextsCollector"]
