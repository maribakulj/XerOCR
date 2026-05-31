"""``RunControl`` — signal d'annulation coopératif d'un run.

Porté à chaque ``Module.execute`` : l'adapter vérifie ``raise_if_cancelled()``
entre deux opérations bloquantes et lève ``RunCancelledError`` si le caller
(utilisateur, deadline globale) a demandé l'arrêt. C'est un concern d'exécution
→ couche 4 (jamais ``domain``).
"""

from __future__ import annotations

import threading

from xerocr.domain.errors import RunCancelledError


class RunControl:
    """Poignée d'annulation coopérative, partagée le temps d'un run.

    Minimal et thread-safe (s'appuie sur ``threading.Event``). L'enregistrement
    de handles d'annulation SDK (pour interrompre un appel réseau en vol) sera
    ajouté **avec son premier consommateur** (adapter LLM, tranche T3/T4) — pas
    spéculé ici (garde-fou « pas de consommateur = supprimé »).
    """

    def __init__(self, cancel_event: threading.Event | None = None) -> None:
        self._cancel = (
            cancel_event if cancel_event is not None else threading.Event()
        )

    def trigger_cancel(self) -> None:
        """Signale l'annulation. Idempotent."""
        self._cancel.set()

    def is_cancelled(self) -> bool:
        return self._cancel.is_set()

    @property
    def cancel_triggered(self) -> bool:
        return self._cancel.is_set()

    def raise_if_cancelled(self) -> None:
        """Lève ``RunCancelledError`` si l'annulation a été demandée."""
        if self._cancel.is_set():
            raise RunCancelledError("run annulé (annulation coopérative).")


__all__ = ["RunControl"]
