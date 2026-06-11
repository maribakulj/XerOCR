"""Vignettes du rapport — orchestration (couche 6).

Résout les **références** image du ``RunResult`` (``RunDocumentResult.image_ref``)
en **vignettes data-URI** via l'adapter (couche 5, Pillow), pour les passer au
renderer comme **intrant de rendu** (les octets ne touchent jamais le résultat).
**Plafond** : au plus ``max_docs`` documents (pires-d'abord par CER), pour borner
le poids hors-ligne ; au-delà, aperçu synthétique. Dégradé gracieux : ``{}`` si
rien n'est résoluble (pas d'image, pas de Pillow).
"""

from __future__ import annotations

from xerocr.adapters.images import thumbnail_data_uri
from xerocr.evaluation.result import RunResult

#: Plafond par défaut de documents vignettés (borne le poids du rapport autonome).
_DEFAULT_MAX_DOCS = 300
#: Fac-similés medium (détail) : plus grands → plafond plus serré.
_FACSIMILE_MAX_PX = 1100
_FACSIMILE_MAX_DOCS = 60


def _worst_first_doc_ids(result: RunResult) -> list[str]:
    """``document_id`` ordonnés par CER décroissant (pires-d'abord), déterministe."""
    worst: dict[str, float] = {}
    for d in result.documents:
        cer = next((s.value for s in d.scores if s.metric == "cer"), None)
        if cer is not None:
            worst[d.document_id] = max(worst.get(d.document_id, 0.0), cer)
    ordered = sorted(worst, key=lambda doc: (-worst[doc], doc))
    # Documents sans CER : ajoutés en fin, ordre d'apparition stable.
    for d in result.documents:
        if d.document_id not in worst and d.document_id not in ordered:
            ordered.append(d.document_id)
    return ordered


def build_thumbnails(
    result: RunResult, *, max_px: int = 280, max_docs: int = _DEFAULT_MAX_DOCS
) -> dict[str, str]:
    """``{document_id: data-URI}`` des vignettes résolues (plafonné, pires-d'abord)."""
    refs: dict[str, str] = {}
    for d in result.documents:
        if d.image_ref and d.document_id not in refs:
            refs[d.document_id] = d.image_ref
    if not refs:
        return {}
    selected = [doc for doc in _worst_first_doc_ids(result) if doc in refs][:max_docs]
    out: dict[str, str] = {}
    for doc_id in selected:
        uri = thumbnail_data_uri(refs[doc_id], max_px=max_px)
        if uri is not None:
            out[doc_id] = uri
    return out


def build_facsimiles(
    result: RunResult,
    *,
    max_px: int = _FACSIMILE_MAX_PX,
    max_docs: int = _FACSIMILE_MAX_DOCS,
) -> dict[str, str]:
    """``{document_id: data-URI}`` des **fac-similés medium** (détail document).

    Même résolution que ``build_thumbnails`` mais plus grands et plus plafonnés
    (le détail montre une image, pas une grille)."""
    return build_thumbnails(result, max_px=max_px, max_docs=max_docs)


__all__ = ["build_facsimiles", "build_thumbnails"]
