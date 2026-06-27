"""Routeur **segmentation** (couche 8) : lancer un run + servir l'image d'un layout.

``POST /api/segmentation/run`` (JSON, **CSRF**) lance un run de **segmentation** sur
un corpus uploadé : `pp_doclayout` (IMAGE→LAYOUT) à travers le **même** ``JobRunner``
que les runs OCR ; le sink (couche 6) persiste le ``CanonicalLayout`` produit, que
``/segmentation`` affiche. **Un seul exécuteur** : un segmenteur est un pipeline,
pas un second chemin. Catégorie distincte des moteurs OCR → endpoint dédié (le
``<select>`` moteur du lanceur reste OCR-only).

Gate : segmenteur **indisponible** (extra ``[segment]`` absent) → ``409``. **Pas**
de masquage mode public : le segmenteur tourne en local sur une image uploadée
(ni clé, ni SSRF). Le corpus vient du ``CorpusStore`` (upload/import déjà validés).

``GET /api/segmentation/{id}/image`` restitue l'image de page persistée (id validé
en amont → ``404`` hors zone/inconnu).
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field

from cinoc.app.corpus_upload import CorpusStore
from cinoc.app.engines import StatusProvider
from cinoc.app.jobs import JobRunner
from cinoc.app.run_planning import (
    SEGMENTER_KIND,
    SEGMENTER_KINDS,
    RunPlanningError,
    plan_segmentation_run,
)
from cinoc.app.segmentation import SegmentationStore
from cinoc.interfaces.web.security.csrf import csrf_protect

#: Type MIME par extension d'image persistée (défaut binaire opaque).
_MEDIA_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
}


class SegmentationRunRequest(BaseModel):
    """Corps d'``POST /api/segmentation/run`` : corpus + segmenteur choisi.

    ``segmenter`` sélectionne le module (``pp_doclayout`` local par défaut, ou
    ``remote_segmenter`` distant). Pour le distant, ``endpoint`` est requis (cible
    object-detection HF) et ``token`` optionnel (auth) — c'est ce qui rend un
    segmenteur tiers **sélectionnable avant le run** sans rien réinstaller.
    """

    model_config = ConfigDict(extra="forbid")

    corpus_id: str = Field(min_length=1, max_length=128)
    segmenter: str = Field(default=SEGMENTER_KIND, max_length=64)
    endpoint: str | None = Field(default=None, max_length=2048)
    token: str | None = Field(default=None, max_length=512)


def build_segmentation_router(
    store: SegmentationStore,
    *,
    runner: JobRunner,
    corpus_store: CorpusStore,
    segmenters: StatusProvider,
) -> APIRouter:
    """Construit le routeur segmentation (monté par ``create_app``)."""
    router = APIRouter()

    @router.post(
        "/api/segmentation/run",
        status_code=201,
        dependencies=[Depends(csrf_protect)],
    )
    def launch_segmentation(req: SegmentationRunRequest) -> dict[str, str]:
        if req.segmenter not in SEGMENTER_KINDS:
            raise HTTPException(
                status_code=422, detail=f"segmenteur inconnu : {req.segmenter}"
            )
        status = next(
            (s for s in segmenters() if s.kind == req.segmenter), None
        )
        if status is None or not status.available:
            detail = status.detail if status else "segmenteur inconnu"
            raise HTTPException(
                status_code=409, detail=f"segmenteur indisponible : {detail}"
            )
        corpus = corpus_store.get(req.corpus_id)
        if corpus is None:
            raise HTTPException(status_code=404, detail="corpus introuvable")
        run_id = f"seg-{uuid.uuid4().hex[:12]}"
        try:
            plan = plan_segmentation_run(
                corpus,
                run_id,
                segmenter=req.segmenter,
                endpoint=req.endpoint,
                token=req.token,
            )
        except RunPlanningError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return {"job_id": runner.launch(plan)}

    @router.get("/api/segmentation/{seg_id}/image")
    def segmentation_image(seg_id: str) -> FileResponse:
        path = store.image_path(seg_id)  # id validé en amont → None hors zone
        if path is None:
            raise HTTPException(status_code=404, detail="image introuvable")
        media = _MEDIA_TYPES.get(path.suffix.lower(), "application/octet-stream")
        return FileResponse(path, media_type=media)

    return router


__all__ = ["SegmentationRunRequest", "build_segmentation_router"]
