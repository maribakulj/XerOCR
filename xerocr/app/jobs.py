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

from xerocr.adapters.storage.history_store import HistoryStore
from xerocr.adapters.storage.job_store import JobState, JobStore
from xerocr.adapters.storage.publisher import NoopPublisher, ResultPublisher
from xerocr.app.history import record_run
from xerocr.app.modules.registry import ModuleRegistry
from xerocr.app.orchestrator import PipelineOutputs
from xerocr.app.orchestrator import run as run_orchestrator
from xerocr.app.results import dump_run_result
from xerocr.app.segmentation import SegmentationStore
from xerocr.domain.artifacts import ArtifactType
from xerocr.domain.errors import RunCancelledError, XerOCRError
from xerocr.domain.layout import CanonicalLayout
from xerocr.domain.run import RunManifest
from xerocr.domain.run_spec import RunSpec
from xerocr.evaluation.result import RunResult
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
        history_store: HistoryStore | None = None,
        segmentation_store: SegmentationStore | None = None,
    ) -> None:
        self._store = store
        self._registry = registry
        self._reports_dir = reports_dir
        self._code_version = code_version
        #: Persistance (S3) : pousse le RunResult vers un dépôt distant. Inactif
        #: par défaut (``NoopPublisher``) → aucun effet réseau sans secret.
        self._publisher = publisher if publisher is not None else NoopPublisher()
        #: Historique longitudinal (S6) : enregistre les agrégats de chaque run
        #: terminé. ``None`` → pas de suivi (rétro-compatible).
        self._history = history_store
        #: Segmentation (S6) : persiste les ``LAYOUT`` produits pour /segmentation.
        #: ``None`` → pas de persistance de mise en page (rétro-compatible).
        self._segmentation = segmentation_store
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
                    artifact_sink=self._persist_layouts,
                )
                self._reports_dir.mkdir(parents=True, exist_ok=True)
                run_id = result.manifest.run_id
                result_path = self._reports_dir / f"{run_id}.json"
                dump_run_result(result, result_path)
                published_url = self._publish_safe(run_id, result_path)
                self._record_safe(result)
        except RunCancelledError:
            self._store.update(job_id, state=JobState.CANCELLED)
        except XerOCRError as exc:
            logger.warning("[jobs] run %s échoué : %s", job_id, exc)
            self._store.update(job_id, state=JobState.FAILED, error=str(exc))
        except Exception as exc:
            # Catch-all **intentionnel** (vérifié Lot G) : un thread worker ne doit
            # jamais mourir en silence — toute erreur inattendue du run est tracée
            # et le job passe FAILED (jamais bloqué en RUNNING).
            logger.warning("[jobs] run %s erreur inattendue : %s", job_id, exc)
            self._store.update(job_id, state=JobState.FAILED, error=str(exc))
        else:
            self._store.update(
                job_id,
                state=JobState.DONE,
                report_name=run_id,
                published_url=published_url,
            )

    def _persist_layouts(
        self, outputs: PipelineOutputs, manifest: RunManifest
    ) -> None:
        """Sink LAYOUT (best-effort) : persiste chaque mise en page produite dans
        le ``SegmentationStore`` pour que ``/segmentation`` visualise les runs
        réels. Un seul exécuteur : la géométrie est un **artefact du run**, pas un
        second chemin. Sans store, ou run sans LAYOUT → no-op. Un échec n'abat pas
        le run (son ``RunResult`` est l'output ; la viz est secondaire)."""
        if self._segmentation is None:
            return
        for pipeline_name, per_document in outputs.items():
            for document_id, artifacts in per_document.items():
                layout_art = artifacts.get(ArtifactType.LAYOUT)
                if layout_art is None or layout_art.uri is None:
                    continue
                try:
                    layout = CanonicalLayout.model_validate_json(
                        Path(layout_art.uri).read_bytes()
                    )
                    self._segmentation.save(layout)
                except (OSError, ValueError) as exc:
                    logger.warning(
                        "[jobs] persistance LAYOUT (%s/%s) échouée : %s",
                        pipeline_name, document_id, exc,
                    )

    def _record_safe(self, result: RunResult) -> None:
        """Enregistre le run dans l'historique (best-effort) : un échec d'écriture
        ne fait **pas** échouer le run — son résultat est déjà écrit et publié."""
        if self._history is None:
            return
        try:
            record_run(self._history, result)
        except Exception as exc:
            # Catch-all **intentionnel** (vérifié Lot G) : l'historique est un
            # effet secondaire. Le narrower laisserait une erreur inattendue
            # remonter au catch-all worker et marquer FAILED un run pourtant
            # **réussi** (RunResult déjà écrit + publié). On trace, on n'échoue pas.
            logger.warning(
                "[jobs] historique de %s échoué : %s", result.manifest.run_id, exc
            )

    def _publish_safe(self, run_id: str, result_path: Path) -> str | None:
        """Publie le résultat (best-effort) : un échec réseau ne fait PAS échouer
        le run — le résultat local est déjà écrit."""
        try:
            return self._publisher.publish(run_id, result_path)
        except Exception as exc:
            # Catch-all **intentionnel** (vérifié Lot G) : `publish` est un effet
            # secondaire au comportement variable (réseau, dépôt distant, impls
            # tierces). Une publication ratée ne doit jamais faire échouer un run
            # réussi (résultat local déjà écrit). On trace, on renvoie None.
            logger.warning("[jobs] publication de %s échouée : %s", run_id, exc)
            return None


__all__ = ["JobRunner", "SpecBuilder"]
