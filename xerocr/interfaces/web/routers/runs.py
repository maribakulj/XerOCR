"""Routeur du **lanceur** : lancer un run, suivre son état, l'annuler (couche 8).

Walking skeleton de TU2.a : ``POST /api/runs`` lance le run de **démonstration**
(``precomputed``, sans clé ni binaire) en arrière-plan via le ``JobRunner`` ;
``GET`` restitue l'état ; ``cancel`` déclenche l'annulation coopérative. Le
``RunResult`` produit atterrit dans le dossier de la vitrine → visible aussitôt.

Sécurité :
- écritures protégées **CSRF** (en-tête custom, cf. ``security/csrf.py``) ;
- **mode public** : les moteurs *cloud* (clé API) sont refusés (``403``) — la
  démo n'utilise que ``precomputed``, donc passe ; le blocage réel des kinds
  cloud est porté par :func:`blocked_cloud_kinds` (sélection de moteur = TU2.b).

Upload de corpus, SSE de progression et sélection de moteur : sous-tranches
suivantes (TU2.b/c).
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from xerocr.app.jobs import JobRunner
from xerocr.domain.run_spec import RunSpec
from xerocr.interfaces.demo import demo_run_spec, write_demo_corpus
from xerocr.interfaces.web.security.csrf import csrf_protect

#: Kinds de moteur **cloud** (porteurs de clé API) refusés en mode public —
#: l'exposition publique ne doit jamais consommer les secrets du mainteneur.
PUBLIC_BLOCKED_KINDS = frozenset({"openai"})

#: Kinds du run de démonstration (TU2.a) : 100 % local → toujours public-safe.
_DEMO_KINDS = frozenset({"precomputed"})


def blocked_cloud_kinds(kinds: Iterable[str]) -> frozenset[str]:
    """Sous-ensemble de ``kinds`` interdit en mode public (intersection cloud)."""
    return frozenset(kinds) & PUBLIC_BLOCKED_KINDS


def build_runs_router(runner: JobRunner, *, public_mode: bool) -> APIRouter:
    """Construit le routeur du lanceur (monté par ``create_app``)."""
    router = APIRouter()

    @router.post(
        "/api/runs", status_code=201, dependencies=[Depends(csrf_protect)]
    )
    def launch_run() -> dict[str, str]:
        blocked = blocked_cloud_kinds(_DEMO_KINDS)
        if public_mode and blocked:
            raise HTTPException(
                status_code=403,
                detail=f"moteur cloud refusé (mode public) : {sorted(blocked)}",
            )
        run_id = f"web-{uuid.uuid4().hex[:12]}"

        def build(workspace: Path) -> RunSpec:
            return demo_run_spec(write_demo_corpus(workspace), run_id=run_id)

        return {"job_id": runner.launch(build)}

    @router.get("/api/runs/{job_id}")
    def get_run(job_id: str) -> dict[str, object]:
        job = runner.store.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="job introuvable")
        return job.model_dump(mode="json")

    @router.post(
        "/api/runs/{job_id}/cancel", dependencies=[Depends(csrf_protect)]
    )
    def cancel_run(job_id: str) -> dict[str, bool]:
        if runner.store.get(job_id) is None:
            raise HTTPException(status_code=404, detail="job introuvable")
        return {"cancelled": runner.cancel(job_id)}

    return router


__all__ = ["PUBLIC_BLOCKED_KINDS", "blocked_cloud_kinds", "build_runs_router"]
