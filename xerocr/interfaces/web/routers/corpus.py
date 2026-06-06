"""Routeur **corpus** : upload ZIP **et** imports distants (couche 8).

``POST /api/corpus`` (multipart, **CSRF**) → ``CorpusStore`` valide et matérialise
une archive. ``POST /api/corpus/import/{iiif,escriptorium,gallica}`` (JSON, **CSRF**)
importent un corpus distant → ``CorpusSpec`` via la couche 6 (même seam
``CorpusStore.materialize``). ``GET /api/corpus/{id}`` restitue le résumé. Tout
corpus stocké est une cible de run.

La taille de l'archive est plafonnée **deux fois** : lecture bornée ici (``413``),
puis quotas fins dans ``extract_corpus_zip`` (``422``).

**Mode public** : les imports distants **fetchent une URL côté serveur** (surface
SSRF) → **refusés en mode public** (``403``), comme les moteurs cloud. L'``_http``
interne bloque déjà les IP non publiques ; on n'ouvre simplement pas la prise sur
un Space exposé. Le token eScriptorium voyage dans le corps (Space privé) et n'est
jamais journalisé.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, ConfigDict, Field

from xerocr.adapters.corpus._http import CorpusHttpError
from xerocr.adapters.corpus.gallica import GallicaArkError
from xerocr.adapters.corpus.huggingface import (
    HuggingFaceConventionError,
    HuggingFaceUnavailableError,
)
from xerocr.app.corpus_import import (
    CorpusImportError,
    import_escriptorium_corpus,
    import_gallica_corpus,
    import_hf_corpus,
    import_iiif_corpus,
)
from xerocr.app.corpus_upload import MAX_ZIP_BYTES, CorpusStore, CorpusUploadError
from xerocr.domain.corpus import CorpusSpec
from xerocr.interfaces.web.security.csrf import csrf_protect

#: Échecs d'import « attendus » (entrée invalide / source injoignable) → 422.
_IMPORT_ERRORS = (
    CorpusImportError,
    CorpusHttpError,
    GallicaArkError,
    HuggingFaceConventionError,
)


class IIIFImportRequest(BaseModel):
    """Corps d'``POST /api/corpus/import/iiif``."""

    model_config = ConfigDict(extra="forbid")

    manifest_url: str = Field(min_length=1, max_length=2048)
    name: str | None = Field(default=None, max_length=128)
    #: Borne le nombre de pages importées (les premières) — protège le Space.
    limit: int | None = Field(default=None, ge=1, le=500)


class EScriptoriumImportRequest(BaseModel):
    """Corps d'``POST /api/corpus/import/escriptorium``."""

    model_config = ConfigDict(extra="forbid")

    base_url: str = Field(min_length=1, max_length=2048)
    token: str = Field(min_length=1, max_length=512)
    doc_pk: int = Field(ge=1)
    name: str | None = Field(default=None, max_length=128)
    layer: str = Field(default="manual", max_length=128)
    limit: int | None = Field(default=None, ge=1, le=2000)


class GallicaImportRequest(BaseModel):
    """Corps d'``POST /api/corpus/import/gallica``."""

    model_config = ConfigDict(extra="forbid")

    ark: str = Field(min_length=1, max_length=512)
    name: str | None = Field(default=None, max_length=128)
    limit: int | None = Field(default=None, ge=1, le=500)
    include_ocr: bool = True


class HuggingFaceImportRequest(BaseModel):
    """Corps d'``POST /api/corpus/import/huggingface``."""

    model_config = ConfigDict(extra="forbid")

    dataset_id: str = Field(min_length=1, max_length=256)
    split: str = Field(default="train", min_length=1, max_length=64)
    name: str | None = Field(default=None, max_length=128)
    #: Borne le nombre de pages **streamées** (les premières) — protège le Space.
    limit: int | None = Field(default=None, ge=1, le=2000)


def build_corpus_router(store: CorpusStore, *, public_mode: bool = False) -> APIRouter:
    """Construit le routeur corpus (upload + imports distants)."""
    router = APIRouter()

    def _materialize(builder: Callable[..., CorpusSpec]) -> dict[str, object]:
        """Gate mode public → matérialise via le store → résumé (erreurs → 422)."""
        if public_mode:
            raise HTTPException(
                status_code=403, detail="import distant refusé (mode public)."
            )
        try:
            corpus_id, spec = store.materialize(builder)
        except HuggingFaceUnavailableError as exc:
            # Extra absent côté serveur (≠ faute de l'appelant) → indisponible.
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except _IMPORT_ERRORS as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return {
            "corpus_id": corpus_id,
            "name": spec.name,
            "n_documents": len(spec.documents),
        }

    @router.post(
        "/api/corpus/import/iiif",
        status_code=201,
        dependencies=[Depends(csrf_protect)],
    )
    def import_iiif(req: IIIFImportRequest) -> dict[str, object]:
        return _materialize(
            lambda dest: import_iiif_corpus(
                req.manifest_url, dest, name=req.name or "iiif", limit=req.limit
            )
        )

    @router.post(
        "/api/corpus/import/escriptorium",
        status_code=201,
        dependencies=[Depends(csrf_protect)],
    )
    def import_escriptorium(req: EScriptoriumImportRequest) -> dict[str, object]:
        return _materialize(
            lambda dest: import_escriptorium_corpus(
                req.base_url,
                req.token,
                req.doc_pk,
                dest,
                name=req.name,
                layer=req.layer,
                limit=req.limit,
            )
        )

    @router.post(
        "/api/corpus/import/gallica",
        status_code=201,
        dependencies=[Depends(csrf_protect)],
    )
    def import_gallica(req: GallicaImportRequest) -> dict[str, object]:
        return _materialize(
            lambda dest: import_gallica_corpus(
                req.ark,
                dest,
                name=req.name,
                limit=req.limit,
                include_ocr=req.include_ocr,
            )
        )

    @router.post(
        "/api/corpus/import/huggingface",
        status_code=201,
        dependencies=[Depends(csrf_protect)],
    )
    def import_huggingface(req: HuggingFaceImportRequest) -> dict[str, object]:
        return _materialize(
            lambda dest: import_hf_corpus(
                req.dataset_id,
                dest,
                name=req.name,
                split=req.split,
                limit=req.limit,
            )
        )

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

    @router.delete(
        "/api/corpus/{corpus_id}", dependencies=[Depends(csrf_protect)]
    )
    def delete_corpus(corpus_id: str) -> dict[str, bool]:
        if not store.delete(corpus_id):
            raise HTTPException(status_code=404, detail="corpus introuvable.")
        return {"deleted": True}

    return router


__all__ = [
    "EScriptoriumImportRequest",
    "GallicaImportRequest",
    "HuggingFaceImportRequest",
    "IIIFImportRequest",
    "build_corpus_router",
]
