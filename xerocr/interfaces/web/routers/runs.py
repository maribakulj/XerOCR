"""Routeur du **lanceur** : lancer un run, suivre son état, l'annuler (couche 8).

TU2.d : ``POST /api/runs`` choisit un **moteur** et, le cas échéant, un **corpus
uploadé** (``corpus_id``). Sans corps → le run de **démonstration** (`precomputed`).

Ordre de garde (sécurité d'abord) :
1. moteur inconnu → ``422`` ;
2. moteur **cloud** en **mode public** → ``403`` (jamais de secret en public) ;
3. moteur de **post-correction** (LLM) en autonome → ``422`` (chaîne OCR→LLM non
   exposée ici ; cf. TU3+) ;
4. ``corpus_id`` fourni mais introuvable → ``404`` ;
5. moteur **indisponible** (binaire/SDK/clé absent) → ``409`` ;
6. incohérence moteur⇄corpus (`precomputed` veut la démo, `tesseract` veut un
   corpus) → ``422``.

``GET`` restitue l'état ; ``cancel`` déclenche l'annulation coopérative. Écritures
protégées **CSRF**. Le ``RunResult`` produit atterrit dans le dossier vitrine.
"""

from __future__ import annotations

import json
import time
import uuid
from collections.abc import Iterator

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict

from xerocr.adapters.storage import JobStore
from xerocr.app.corpus_upload import CorpusStore
from xerocr.app.engines import CLOUD_KINDS, StatusProvider
from xerocr.app.jobs import JobRunner, SpecBuilder
from xerocr.domain.artifacts import ArtifactType
from xerocr.domain.corpus import CorpusSpec
from xerocr.domain.evaluation import EvaluationSpec, EvaluationView
from xerocr.domain.pipeline import PipelineSpec, PipelineStep
from xerocr.domain.run_spec import RunSpec
from xerocr.interfaces.demo import demo_run_spec, write_demo_corpus
from xerocr.interfaces.web.security.csrf import csrf_protect

#: Kinds de **post-correction** LLM : pas de run autonome (chaîne OCR→LLM = TU3+).
#: (Les kinds *cloud* bloqués en mode public sont ``CLOUD_KINDS`` — source unique
#: en couche 6, ``app.engines`` ; on ne les redéclare pas ici.)
LLM_KINDS = frozenset({"openai", "ollama"})

_OCR_VIEW = EvaluationView(
    name="text",
    candidate_types=frozenset({ArtifactType.RAW_TEXT}),
    metric_names=("cer", "wer", "mer"),
)


class LaunchRequest(BaseModel):
    """Corps (optionnel) du lancement : un moteur, et un corpus uploadé ou rien."""

    model_config = ConfigDict(extra="forbid")

    engine: str = "precomputed"
    corpus_id: str | None = None


def _tesseract_spec(corpus: CorpusSpec, run_id: str, *, lang: str = "fra") -> RunSpec:
    label = "tesseract"
    step = PipelineStep(
        id="ocr",
        kind="ocr",
        adapter_name=f"tesseract:{label}",
        input_types=(ArtifactType.IMAGE,),
        output_types=(ArtifactType.RAW_TEXT,),
    )
    return RunSpec(
        corpus=corpus,
        pipelines=(PipelineSpec(name=label, initial_inputs=(ArtifactType.IMAGE,),
                                steps=(step,)),),
        evaluation=EvaluationSpec(views=(_OCR_VIEW,)),
        adapter_kwargs={f"tesseract:{label}": {"label": label, "lang": lang}},
        run_id=run_id,
    )


def _spec_builder(engine: str, corpus: CorpusSpec | None, run_id: str) -> SpecBuilder:
    """Construit le *builder* de spec pour (moteur, corpus) — ou refuse (``422``)."""
    if engine == "precomputed":
        if corpus is not None:
            raise HTTPException(
                status_code=422,
                detail="precomputed = démonstration (ne s'exécute pas sur un corpus).",
            )
        return lambda ws: demo_run_spec(write_demo_corpus(ws), run_id=run_id)
    # engine == "tesseract" (seul OCR réel du socle exécutable sur un corpus)
    if corpus is None:
        raise HTTPException(status_code=422, detail="tesseract : corpus_id requis.")
    return lambda _ws: _tesseract_spec(corpus, run_id)


def _parse_last_event_id(raw: str | None) -> int:
    """``Last-Event-ID`` (en-tête de reprise SSE) → entier ≥ 0, tolérant."""
    if raw is None:
        return 0
    try:
        return max(0, int(raw))
    except ValueError:
        return 0


def _sse_stream(
    store: JobStore,
    job_id: str,
    last_event_id: int,
    *,
    poll: float = 0.1,
    idle_timeout: float = 30.0,
) -> Iterator[str]:
    """Diffuse le journal du job en SSE depuis ``last_event_id`` jusqu'au terminal.

    Boucle de *polling* (les transitions sont rares) ; rejoue d'abord les
    événements manqués (reprise ``Last-Event-ID``), puis suit les nouveaux. Un
    job déjà terminé renvoie tout l'historique puis ferme. Le ``idle_timeout``
    borne un job qui ne se terminerait jamais (pas de flux pendu en prod).
    """
    sent = last_event_id
    deadline = time.monotonic() + idle_timeout
    while True:
        for event_id, job in store.history_since(job_id, sent):
            sent = event_id
            payload = json.dumps(job.model_dump(mode="json"), ensure_ascii=False)
            yield f"id: {event_id}\nevent: {job.state.value}\ndata: {payload}\n\n"
            deadline = time.monotonic() + idle_timeout
        current = store.get(job_id)
        if current is not None and current.state.is_terminal:
            if not store.history_since(job_id, sent):
                return
        elif time.monotonic() > deadline:
            return
        time.sleep(poll)


def build_runs_router(
    runner: JobRunner,
    corpus_store: CorpusStore,
    *,
    public_mode: bool,
    statuses: StatusProvider,
) -> APIRouter:
    """Construit le routeur du lanceur (monté par ``create_app``)."""
    router = APIRouter()

    @router.post(
        "/api/runs", status_code=201, dependencies=[Depends(csrf_protect)]
    )
    def launch_run(payload: LaunchRequest | None = None) -> dict[str, str]:
        req = payload or LaunchRequest()
        sts = statuses()
        if req.engine not in {s.kind for s in sts}:
            raise HTTPException(
                status_code=422, detail=f"moteur inconnu : {req.engine!r}"
            )
        if public_mode and req.engine in CLOUD_KINDS:
            raise HTTPException(
                status_code=403,
                detail=f"moteur cloud refusé (mode public) : {req.engine!r}",
            )
        if req.engine in LLM_KINDS:
            raise HTTPException(
                status_code=422,
                detail="post-correction LLM : chaîne OCR→LLM non exposée ici (TU3+).",
            )
        corpus: CorpusSpec | None = None
        if req.corpus_id is not None:
            corpus = corpus_store.get(req.corpus_id)
            if corpus is None:
                raise HTTPException(status_code=404, detail="corpus introuvable")
        if req.engine not in {s.kind for s in sts if s.available}:
            raise HTTPException(
                status_code=409, detail=f"moteur indisponible : {req.engine!r}"
            )
        run_id = f"web-{uuid.uuid4().hex[:12]}"
        build = _spec_builder(req.engine, corpus, run_id)
        return {"job_id": runner.launch(build)}

    @router.get("/api/runs/{job_id}")
    def get_run(job_id: str) -> dict[str, object]:
        job = runner.store.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="job introuvable")
        return job.model_dump(mode="json")

    @router.get("/api/runs/{job_id}/events")
    def run_events(job_id: str, request: Request) -> StreamingResponse:
        if runner.store.get(job_id) is None:
            raise HTTPException(status_code=404, detail="job introuvable")
        last = _parse_last_event_id(request.headers.get("last-event-id"))
        return StreamingResponse(
            _sse_stream(runner.store, job_id, last),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @router.post(
        "/api/runs/{job_id}/cancel", dependencies=[Depends(csrf_protect)]
    )
    def cancel_run(job_id: str) -> dict[str, bool]:
        if runner.store.get(job_id) is None:
            raise HTTPException(status_code=404, detail="job introuvable")
        return {"cancelled": runner.cancel(job_id)}

    return router


__all__ = ["LLM_KINDS", "LaunchRequest", "build_runs_router"]
