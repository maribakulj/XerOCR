"""Stockage (couche 5) : état des jobs de run lancés via le web/CLI long.

Démarre **en mémoire** (TU2.a) : suffit au walking skeleton du lanceur. La
table d'événements + la reprise SSE ``Last-Event-ID`` (réf. ANALYSE_COUCHE_5
R-10) sont la **sous-tranche suivante** (TU2.c), pas ici.
"""

from __future__ import annotations

from xerocr.adapters.storage.job_store import Job, JobState, JobStore

__all__ = ["Job", "JobState", "JobStore"]
