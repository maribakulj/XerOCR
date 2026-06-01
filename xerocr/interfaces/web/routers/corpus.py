"""Routeur d'**upload de corpus** : reçoit un ZIP, le valide, le stocke (couche 8).

``POST /api/corpus`` (multipart, **CSRF**) → ``CorpusStore`` (couche 6) qui valide
et matérialise l'archive ; ``GET /api/corpus/{id}`` en restitue le résumé. Le
corpus stocké sera la cible d'un run à la sous-tranche suivante (TU2.d).

La taille est plafonnée **deux fois** : lecture bornée ici (``413`` net si
dépassement), puis quotas fins dans ``extract_corpus_zip`` (``422``).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from xerocr.app.corpus_upload import MAX_ZIP_BYTES, CorpusStore, CorpusUploadError
from xerocr.interfaces.web.security.csrf import csrf_protect


def build_corpus_router(store: CorpusStore) -> APIRouter:
    """Construit le routeur d'upload de corpus (monté par ``create_app``)."""
    router = APIRouter()

    @router.post(
        "/api/corpus", status_code=201, dependencies=[Depends(csrf_protect)]
    )
    async def upload_corpus(
        file: Annotated[UploadFile, File()],
    ) -> dict[str, object]:
        data = await file.read(MAX_ZIP_BYTES + 1)
        if len(data) > MAX_ZIP_BYTES:
            raise HTTPException(status_code=413, detail="archive trop volumineuse.")
        try:
            corpus_id, spec = store.save(file.filename or "corpus", data)
        except CorpusUploadError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return {
            "corpus_id": corpus_id,
            "name": spec.name,
            "n_documents": len(spec.documents),
        }

    @router.get("/api/corpus/{corpus_id}")
    def corpus_summary(corpus_id: str) -> dict[str, object]:
        spec = store.get(corpus_id)
        if spec is None:
            raise HTTPException(status_code=404, detail="corpus introuvable.")
        return {
            "corpus_id": corpus_id,
            "name": spec.name,
            "n_documents": len(spec.documents),
            "documents": [doc.id for doc in spec.documents],
        }

    return router


__all__ = ["build_corpus_router"]
