"""Routeur du **lanceur** : lancer un run, suivre son état, l'annuler (couche 8).

``POST /api/runs`` choisit des **concurrents** (chacun = un pipeline : OCR seul,
OCR→LLM texte/image, ou VLM zero-shot) sur un **corpus** (``corpus_id``). N
concurrents → **un seul run** comparé (cross-engine). Sans concurrent → le run de
**démonstration** (``precomputed``, local).

Ordre de garde, par moteur référencé (``engine`` + ``llm``) :
1. moteur inconnu → ``422`` ;
2. **mode public** : moteur hors du socle gratuit (``PUBLIC_ENGINE_KINDS``) → ``403``
   (fail-closed) — les moteurs cloud (clé) et tout futur kind y tombent, même si une
   clé est posée ; seul ``tesseract`` (gratuit, local) reste exécutable publiquement ;
3. ``corpus_id`` fourni mais introuvable → ``404`` ;
4. moteur **indisponible** (binaire/SDK/clé absent) → ``409`` — hors mode public, un
   moteur cloud sans clé y tombe ; avec sa clé il est autorisé (clé posée → marche) ;
5. concurrent incohérent (mode⇄moteur) → ``422`` (``plan_benchmark_run``).

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
from pydantic import BaseModel, ConfigDict, Field

from xerocr.adapters.storage import JobStore
from xerocr.app.corpus_upload import CorpusStore
from xerocr.app.engines import PUBLIC_ENGINE_KINDS, StatusProvider
from xerocr.app.jobs import JobRunner
from xerocr.app.run_planning import Competitor, RunPlanningError, plan_benchmark_run
from xerocr.domain.corpus import CorpusSpec
from xerocr.interfaces.demo import demo_spec_builder
from xerocr.interfaces.web.security.csrf import csrf_protect


class LaunchRequest(BaseModel):
    """Corps (optionnel) : des concurrents + un corpus, ou rien (démonstration)."""

    model_config = ConfigDict(extra="forbid")

    competitors: tuple[Competitor, ...] = ()
    corpus_id: str | None = None
    normalization: str | None = None
    #: Caractères filtrés des deux côtés (GT/hyp) avant le calcul des métriques.
    char_exclude: str | None = Field(default=None, max_length=512)
    #: Nom d'un profil de métriques (``standard``/``essentiel``/``philologie``) :
    #: choisit les colonnes de classement de la vue ``text``. Inconnu → 422 (plan).
    metric_profile: str | None = Field(default=None, max_length=64)


def _referenced_kinds(comp: Competitor) -> tuple[str, ...]:
    """Kinds qu'un concurrent met en jeu : moteur OCR/VLM + LLM éventuel."""
    return (comp.engine,) if comp.llm is None else (comp.engine, comp.llm)


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
    statuses: StatusProvider,
    public_mode: bool = False,
) -> APIRouter:
    """Construit le routeur du lanceur (monté par ``create_app``).

    ``public_mode`` (Space exposé) **verrouille** l'exécution au seul socle
    first-party gratuit (``PUBLIC_ENGINE_KINDS``) : tout moteur cloud ou autre kind
    est refusé en ``403`` (fail-closed), sans jamais lancer un appel facturé.
    """
    router = APIRouter()

    @router.post(
        "/api/runs", status_code=201, dependencies=[Depends(csrf_protect)]
    )
    def launch_run(payload: LaunchRequest | None = None) -> dict[str, str]:
        req = payload or LaunchRequest()
        run_id = f"web-{uuid.uuid4().hex[:12]}"
        # Démonstration : aucun concurrent → precomputed (local, jamais cloud).
        if not req.competitors:
            if req.corpus_id is not None:
                raise HTTPException(
                    status_code=422,
                    detail="démonstration : ne s'exécute pas sur un corpus "
                    "(sélectionne au moins un concurrent).",
                )
            return {"job_id": runner.launch(demo_spec_builder(run_id))}

        sts = statuses()
        known = {s.kind for s in sts}
        available = {s.kind for s in sts if s.available}
        # 1 : moteur connu (la disponibilité runtime — binaire/SDK/clé — est
        # vérifiée à l'étape 4 : un moteur cloud sans clé y tombe en 409).
        for comp in req.competitors:
            for kind in _referenced_kinds(comp):
                if kind not in known:
                    raise HTTPException(
                        status_code=422, detail=f"moteur inconnu : {kind!r}"
                    )
        # 2 : mode public → fail-closed sur le socle gratuit. Refusé AVANT toute
        # vérification de clé/dispo : un moteur cloud ne doit pas même être tenté
        # sur une instance publique (aucun appel facturé), clé présente ou non.
        if public_mode:
            for comp in req.competitors:
                for kind in _referenced_kinds(comp):
                    if kind not in PUBLIC_ENGINE_KINDS:
                        raise HTTPException(
                            status_code=403,
                            detail=f"moteur indisponible en mode public : {kind!r} "
                            "(seul le socle gratuit est exécuté).",
                        )
        # 3 : corpus.
        corpus: CorpusSpec | None = None
        if req.corpus_id is not None:
            corpus = corpus_store.get(req.corpus_id)
            if corpus is None:
                raise HTTPException(status_code=404, detail="corpus introuvable")
        # 4 : disponibilité runtime (binaire/SDK/clé).
        for comp in req.competitors:
            for kind in _referenced_kinds(comp):
                if kind not in available:
                    raise HTTPException(
                        status_code=409, detail=f"moteur indisponible : {kind!r}"
                    )
        # 5 : cohérence mode⇄moteur (dispatch exhaustif).
        try:
            build = plan_benchmark_run(
                req.competitors,
                corpus,
                run_id,
                normalization=req.normalization,
                char_exclude=req.char_exclude,
                metric_profile=req.metric_profile,
            )
        except RunPlanningError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return {"job_id": runner.launch(build)}

    @router.post(
        "/api/runs/config", dependencies=[Depends(csrf_protect)]
    )
    def validate_config(payload: LaunchRequest) -> dict[str, object]:
        """Valide une **config de lanceur** (= un ``LaunchRequest``) et la renvoie
        sous forme **canonique**.

        Stateless : aucune persistance (XerOCR reste déterministe). Consommé par
        l'**import** côté client, qui valide ici le fichier déposé avant de
        repeupler le formulaire — un champ inconnu ou une borne dépassée tombe en
        ``422`` (Pydantic, ``extra="forbid"``), jamais un repeuplement muet.
        """
        return {"config": payload.model_dump(mode="json", exclude_none=True)}

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


__all__ = ["Competitor", "LaunchRequest", "build_runs_router"]
