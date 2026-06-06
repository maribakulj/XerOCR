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

from xerocr.app.corpus_upload import CorpusStore
from xerocr.app.engines import StatusProvider
from xerocr.app.jobs import JobRunner
from xerocr.app.segmentation import SegmentationStore
from xerocr.domain.artifacts import ArtifactType
from xerocr.domain.corpus import CorpusSpec
from xerocr.domain.evaluation import EvaluationSpec
from xerocr.domain.pipeline import PipelineSpec, PipelineStep
from xerocr.domain.run_spec import RunSpec
from xerocr.interfaces.web.security.csrf import csrf_protect

#: Kind du segmenteur du socle lancé par cet endpoint.
_SEGMENTER_KIND = "pp_doclayout"

#: Type MIME par extension d'image persistée (défaut binaire opaque).
_MEDIA_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
}


class SegmentationRunRequest(BaseModel):
    """Corps d'``POST /api/segmentation/run`` : le corpus à segmenter."""

    model_config = ConfigDict(extra="forbid")

    corpus_id: str = Field(min_length=1, max_length=128)


def _segmentation_spec(corpus: CorpusSpec, run_id: str) -> RunSpec:
    """Pipeline de segmentation à 1 étape : ``pp_doclayout`` (IMAGE→LAYOUT).

    Aucune vue d'évaluation : un run de segmentation produit de la **géométrie**
    (captée par le sink), pas une métrique scalaire. Le ``RunResult`` reste
    l'output formel du run (sans score), la visualisation vit sur ``/segmentation``.
    """
    step = PipelineStep(
        id="seg",
        kind="layout",
        adapter_name=_SEGMENTER_KIND,
        input_types=(ArtifactType.IMAGE,),
        output_types=(ArtifactType.LAYOUT,),
    )
    return RunSpec(
        corpus=corpus,
        pipelines=(
            PipelineSpec(
                name=_SEGMENTER_KIND,
                initial_inputs=(ArtifactType.IMAGE,),
                steps=(step,),
            ),
        ),
        evaluation=EvaluationSpec(views=()),
        run_id=run_id,
    )


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
        available = any(
            s.available for s in segmenters() if s.kind == _SEGMENTER_KIND
        )
        if not available:
            raise HTTPException(
                status_code=409,
                detail="segmenteur indisponible (extra [segment] requis).",
            )
        corpus = corpus_store.get(req.corpus_id)
        if corpus is None:
            raise HTTPException(status_code=404, detail="corpus introuvable")
        run_id = f"seg-{uuid.uuid4().hex[:12]}"
        return {
            "job_id": runner.launch(lambda _ws: _segmentation_spec(corpus, run_id))
        }

    @router.get("/api/segmentation/{seg_id}/image")
    def segmentation_image(seg_id: str) -> FileResponse:
        path = store.image_path(seg_id)  # id validé en amont → None hors zone
        if path is None:
            raise HTTPException(status_code=404, detail="image introuvable")
        media = _MEDIA_TYPES.get(path.suffix.lower(), "application/octet-stream")
        return FileResponse(path, media_type=media)

    return router


__all__ = ["SegmentationRunRequest", "build_segmentation_router"]
