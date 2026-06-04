"""Routeur **corpus** : upload ZIP **et** import distant IIIF (couche 8).

``POST /api/corpus`` (multipart, **CSRF**) → ``CorpusStore`` valide et matérialise
une archive ; ``POST /api/corpus/import/iiif`` (JSON, **CSRF**) importe un
manifeste IIIF → ``CorpusSpec`` (images) via la couche 6 ; ``GET /api/corpus/{id}``
restitue le résumé. Le corpus stocké est la cible d'un run.

La taille de l'archive est plafonnée **deux fois** : lecture bornée ici (``413``),
puis quotas fins dans ``extract_corpus_zip`` (``422``).

**Mode public** : l'import distant **fetch une URL côté serveur** (surface SSRF) →
**refusé en mode public** (``403``), comme les moteurs cloud. L'``_http`` interne
bloque déjà les IP non publiques ; on n'ouvre simplement pas cette prise sur un
Space exposé.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, ConfigDict, Field

from xerocr.adapters.corpus._http import CorpusHttpError
from xerocr.app.corpus_import import CorpusImportError, import_iiif_corpus
from xerocr.app.corpus_upload import MAX_ZIP_BYTES, CorpusStore, CorpusUploadError
from xerocr.interfaces.web.security.csrf import csrf_protect


class IIIFImportRequest(BaseModel):
    """Corps d'``POST /api/corpus/import/iiif``."""

    model_config = ConfigDict(extra="forbid")

    manifest_url: str = Field(min_length=1, max_length=2048)
    name: str | None = Field(default=None, max_length=128)
    #: Borne le nombre de pages importées (les premières) — protège le Space.
    limit: int | None = Field(default=None, ge=1, le=500)


def build_corpus_router(store: CorpusStore, *, public_mode: bool = False) -> APIRouter:
    """Construit le routeur corpus (upload + import IIIF) monté par ``create_app``."""
    router = APIRouter()

    @router.post(
        "/api/corpus/import/iiif",
        status_code=201,
        dependencies=[Depends(csrf_protect)],
    )
    def import_iiif(req: IIIFImportRequest) -> dict[str, object]:
        if public_mode:
            raise HTTPException(
                status_code=403, detail="import distant refusé (mode public)."
            )
        name = req.name or "iiif"
        try:
            corpus_id, spec = store.materialize(
                lambda dest: import_iiif_corpus(
                    req.manifest_url, dest, name=name, limit=req.limit
                )
            )
        except (CorpusImportError, CorpusHttpError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return {
            "corpus_id": corpus_id,
            "name": spec.name,
            "n_documents": len(spec.documents),
        }

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
