"""``JobStore`` — état des jobs de run, **en mémoire et thread-safe** (couche 5).

Un job = une exécution asynchrone d'un ``RunSpec`` (lancée par le ``JobRunner``,
couche 6). Le store ne *fait* rien : il garde l'état observable (la machine à
états ci-dessous) pour que le web le restitue et qu'un ``cancel`` soit traçable.

Concurrence : un seul verrou protège le dict ; ``Job`` est **immuable** (pydantic
``frozen``), donc un lecteur (requête HTTP) reçoit un instantané cohérent sans
risque de course avec le worker qui le remplace sous verrou.
"""

from __future__ import annotations

import threading
import uuid
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from xerocr.domain.errors import XerOCRError
from xerocr.domain.run import utcnow


class JobState(StrEnum):
    """États d'un job. Terminaux : ``DONE``, ``FAILED``, ``CANCELLED``."""

    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @property
    def is_terminal(self) -> bool:
        return self in _TERMINAL


_TERMINAL = frozenset({JobState.DONE, JobState.FAILED, JobState.CANCELLED})


class JobError(XerOCRError):
    """Job introuvable."""


class Job(BaseModel):
    """Instantané immuable de l'état d'un job."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    state: JobState
    created_at: str
    updated_at: str
    #: Stem du ``RunResult`` JSON écrit quand ``state == DONE`` (sinon ``None``).
    report_name: str | None = None
    #: Message d'erreur quand ``state == FAILED`` (sinon ``None``).
    error: str | None = None


class JobStore:
    """Dictionnaire thread-safe ``job_id → Job`` (instantanés immuables)."""

    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()

    def create(self) -> Job:
        """Crée un job ``PENDING`` (id généré) et le renvoie."""
        now = utcnow().isoformat()
        job = Job(id=uuid.uuid4().hex, state=JobState.PENDING, created_at=now,
                  updated_at=now)
        with self._lock:
            self._jobs[job.id] = job
        return job

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def list(self) -> tuple[Job, ...]:
        """Tous les jobs, du plus récent au plus ancien."""
        with self._lock:
            jobs = tuple(self._jobs.values())
        return tuple(sorted(jobs, key=lambda j: j.created_at, reverse=True))

    def update(
        self,
        job_id: str,
        *,
        state: JobState,
        report_name: str | None = None,
        error: str | None = None,
    ) -> Job:
        """Remplace l'instantané du job (sous verrou). Lève si inconnu."""
        with self._lock:
            current = self._jobs.get(job_id)
            if current is None:
                raise JobError(f"job {job_id!r} introuvable.")
            updated = current.model_copy(
                update={
                    "state": state,
                    "report_name": report_name,
                    "error": error,
                    "updated_at": utcnow().isoformat(),
                }
            )
            self._jobs[job_id] = updated
        return updated


__all__ = ["Job", "JobError", "JobState", "JobStore"]
