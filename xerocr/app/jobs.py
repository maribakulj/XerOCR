"""``JobRunner`` — exécute un run **en arrière-plan**, annulable (couche 6).

Le walking skeleton du lanceur (TU2.a) : on lance ``orchestrator.run`` dans un
thread *daemon*, on suit son état dans le ``JobStore`` (couche 5), et on câble
l'**annulation coopérative** via ``RunControl`` (couche 4) — un ``cancel`` HTTP
déclenche le signal que l'exécuteur sonde entre deux étapes.

Le corpus est matérialisé par un *builder* dans un workspace temporaire **propre
au job**, vivant le temps du run puis nettoyé : le run lit ses fichiers avant la
fin. Le ``RunResult`` est écrit en JSON dans ``reports_dir`` → il apparaît
aussitôt dans la vitrine read-only existante (preuve de bout en bout).

SSE/progression fine et upload de corpus = sous-tranches suivantes (TU2.b/c).
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from pathlib import Path
from tempfile import TemporaryDirectory

from xerocr.adapters.storage.job_store import JobState, JobStore
from xerocr.adapters.storage.publisher import NoopPublisher, ResultPublisher
from xerocr.app.modules.registry import ModuleRegistry
from xerocr.app.orchestrator import run as run_orchestrator
from xerocr.app.results import dump_run_result
from xerocr.domain.errors import RunCancelledError, XerOCRError
from xerocr.domain.run_spec import RunSpec
from xerocr.pipeline.run_control import RunControl

logger = logging.getLogger(__name__)

#: Construit le ``RunSpec`` d'un job en matérialisant son corpus dans le
#: workspace fourni (vivant le temps du run).
SpecBuilder = Callable[[Path], RunSpec]


class JobRunner:
    """Lance et suit des runs asynchrones, écrivant leurs ``RunResult``."""

    def __init__(
        self,
        *,
        store: JobStore,
        registry: ModuleRegistry,
        reports_dir: Path,
        code_version: str,
        publisher: ResultPublisher | None = None,
    ) -> None:
        self._store = store
        self._registry = registry
        self._reports_dir = reports_dir
        self._code_version = code_version
        #: Persistance (S3) : pousse le RunResult vers un dépôt distant. Inactif
        #: par défaut (``NoopPublisher``) → aucun effet réseau sans secret.
        self._publisher = publisher if publisher is not None else NoopPublisher()
        self._controls: dict[str, RunControl] = {}
        self._threads: dict[str, threading.Thread] = {}
        self._lock = threading.Lock()

    @property
    def store(self) -> JobStore:
        """Le ``JobStore`` lu par le web pour restituer l'état des jobs."""
        return self._store

    def launch(self, build_spec: SpecBuilder) -> str:
        """Crée un job, démarre son thread, renvoie son identifiant."""
        job = self._store.create()
        control = RunControl()
        thread = threading.Thread(
            target=self._execute,
            args=(job.id, build_spec, control),
            name=f"xerocr-job-{job.id[:8]}",
            daemon=True,
        )
        with self._lock:
            self._controls[job.id] = control
            self._threads[job.id] = thread
        thread.start()
        return job.id

    def cancel(self, job_id: str) -> bool:
        """Demande l'annulation coopérative du job. ``False`` si inconnu/fini."""
        with self._lock:
            control = self._controls.get(job_id)
        job = self._store.get(job_id)
        if control is None or job is None or job.state.is_terminal:
            return False
        control.trigger_cancel()
        return True

    def join(self, job_id: str, timeout: float = 10.0) -> bool:
        """Attend la fin du thread du job (usage tests). ``True`` si terminé."""
        with self._lock:
            thread = self._threads.get(job_id)
        if thread is None:
            return False
        thread.join(timeout)
        return not thread.is_alive()

    def _execute(
        self, job_id: str, build_spec: SpecBuilder, control: RunControl
    ) -> None:
        self._store.update(job_id, state=JobState.RUNNING)
        try:
            with TemporaryDirectory(prefix="xerocr-job-") as workspace:
                spec = build_spec(Path(workspace))
                result = run_orchestrator(
                    spec,
                    registry=self._registry,
                    code_version=self._code_version,
                    control=control,
                )
                self._reports_dir.mkdir(parents=True, exist_ok=True)
                run_id = result.manifest.run_id
                result_path = self._reports_dir / f"{run_id}.json"
                dump_run_result(result, result_path)
                published_url = self._publish_safe(run_id, result_path)
        except RunCancelledError:
            self._store.update(job_id, state=JobState.CANCELLED)
        except XerOCRError as exc:
            logger.warning("[jobs] run %s échoué : %s", job_id, exc)
            self._store.update(job_id, state=JobState.FAILED, error=str(exc))
        except Exception as exc:  # le worker ne doit jamais mourir en silence
            logger.warning("[jobs] run %s erreur inattendue : %s", job_id, exc)
            self._store.update(job_id, state=JobState.FAILED, error=str(exc))
        else:
            self._store.update(
                job_id,
                state=JobState.DONE,
                report_name=run_id,
                published_url=published_url,
            )

    def _publish_safe(self, run_id: str, result_path: Path) -> str | None:
        """Publie le résultat (best-effort) : un échec réseau ne fait PAS échouer
        le run — le résultat local est déjà écrit."""
        try:
            return self._publisher.publish(run_id, result_path)
        except Exception as exc:  # best-effort : on trace, on n'échoue pas
            logger.warning("[jobs] publication de %s échouée : %s", run_id, exc)
            return None


__all__ = ["JobRunner", "SpecBuilder"]
