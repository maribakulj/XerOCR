"""Routeur **transcription hybride** (couche 8) : lancer un run seg → OCR → ALTO.

``POST /api/hybrid/run`` (JSON, **CSRF**) lance un pipeline **hybride**
(segmentation → reconnaissance par région → assemblage ALTO) sur un corpus de la
bibliothèque, via le **même** ``JobRunner`` que les runs OCR/segmentation. Aucun
second chemin d'exécution. Les sorties sont persistées par les sinks déjà câblés :
``ALTO_XML`` → ``AltoStore`` (téléchargeable par ``/reports/{run_id}/alto.zip``)
et ``LAYOUT`` → ``SegmentationStore`` (régions visibles par ``/segmentation``).

Gate : segmenteur **ou** OCR par région indisponible (extra/binaire absent) →
``409`` (jamais un run voué à l'échec). Le mode ``precomputed`` (démo/CI) n'a pas
de prérequis → pas de gate. Construction de spec déléguée à ``plan_hybrid_run``
(couche ``app``) — le routeur reste du transport mince (``test_interfaces_thin``).
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from cinoc.app.corpus_upload import CorpusStore
from cinoc.app.engines import StatusProvider
from cinoc.app.jobs import JobRunner
from cinoc.app.run_planning import RunPlanningError
from cinoc.app.structure_planning import plan_hybrid_run
from cinoc.interfaces.web.security.csrf import csrf_protect

#: Briques ``precomputed`` (démo/CI) : aucun extra/binaire → pas de gate de dispo.
_PRECOMPUTED = frozenset({"precomputed_layout", "precomputed_region"})


class HybridRunRequest(BaseModel):
    """Corps d'``POST /api/hybrid/run`` : corpus + segmenteur + OCR par région.

    Réel par défaut : ``pp_doclayout`` (segmentation) + ``tesseract`` (OCR par
    bloc). ``remote_segmenter`` exige ``endpoint`` ; ``precomputed_region`` exige
    ``source_label`` (mode démo). ``label`` nomme l'identité du moteur OCR.
    """

    model_config = ConfigDict(extra="forbid")

    corpus_id: str = Field(min_length=1, max_length=128)
    segmenter: str = Field(default="pp_doclayout", max_length=64)
    ocr: str = Field(default="tesseract", max_length=64)
    label: str = Field(default="hybrid", max_length=64)
    source_label: str | None = Field(default=None, max_length=64)
    endpoint: str | None = Field(default=None, max_length=2048)
    token: str | None = Field(default=None, max_length=512)
    lang: str = Field(default="fra", max_length=32)
    model: str | None = Field(default=None, max_length=128)
    prompt: str | None = Field(default=None, max_length=4096)


def build_hybrid_router(
    *,
    runner: JobRunner,
    corpus_store: CorpusStore,
    segmenters: StatusProvider,
    engines: StatusProvider,
) -> APIRouter:
    """Construit le routeur de transcription hybride (monté par ``create_app``)."""
    router = APIRouter()

    def _require_available(
        kind: str, provider: StatusProvider, label: str
    ) -> None:
        if kind in _PRECOMPUTED:
            return
        status = next((s for s in provider() if s.kind == kind), None)
        if status is None or not status.available:
            detail = status.detail if status else "inconnu"
            raise HTTPException(
                status_code=409, detail=f"{label} indisponible : {detail}"
            )

    @router.post(
        "/api/hybrid/run",
        status_code=201,
        dependencies=[Depends(csrf_protect)],
    )
    def launch_hybrid(req: HybridRunRequest) -> dict[str, str]:
        corpus = corpus_store.get(req.corpus_id)
        if corpus is None:
            raise HTTPException(status_code=404, detail="corpus introuvable")
        run_id = f"hyb-{uuid.uuid4().hex[:12]}"
        try:
            plan = plan_hybrid_run(
                corpus,
                run_id,
                segmenter=req.segmenter,
                ocr=req.ocr,
                label=req.label,
                source_label=req.source_label,
                endpoint=req.endpoint,
                token=req.token,
                lang=req.lang,
                model=req.model,
                prompt=req.prompt,
            )
        except RunPlanningError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        _require_available(req.segmenter, segmenters, "segmenteur")
        _require_available(req.ocr, engines, "reconnaisseur par région")
        return {"job_id": runner.launch(plan), "run_id": run_id}

    return router


__all__ = ["HybridRunRequest", "build_hybrid_router"]
