"""Stockage (couche 5) : état des jobs de run lancés via le web/CLI long.

En mémoire par choix : suffit au lanceur mono-worker du Space. Le journal
d'événements du ``JobStore`` porte la reprise SSE ``Last-Event-ID`` (réserve
R-10 d'ANALYSE_COUCHE_5, levée).
"""

from __future__ import annotations

from xerocr.adapters.storage.history_store import (
    HistoryRecord,
    HistoryStore,
    Regression,
)
from xerocr.adapters.storage.job_store import Job, JobState, JobStore

__all__ = [
    "HistoryRecord",
    "HistoryStore",
    "Job",
    "JobState",
    "JobStore",
    "Regression",
]
