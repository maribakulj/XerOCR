"""Orchestrateur de run (couche 6) — **coquille mince qui ne calcule pas**.

Câble les couches internes : construit les modules (registre), fait tourner
l'exécuteur (couche 4) par document, passe les artefacts au runner d'évaluation
(couche 3), assemble le ``RunResult`` + le ``RunManifest``. Il **n'évalue rien
lui-même** (l'assemblage métrique vit en ``evaluation``) et **n'exécute aucun
moteur** (les modules le font).

Mono-thread, séquentiel par choix : le parallélisme viendrait avec un
consommateur réel (gros corpus), pas avant.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from xerocr.app.modules.registry import ModuleRegistry
from xerocr.domain.artifacts import Artifact, ArtifactType
from xerocr.domain.deadline import Deadline
from xerocr.domain.documents import DocumentRef
from xerocr.domain.errors import AdapterStepError, XerOCRError
from xerocr.domain.run import RunManifest, utcnow
from xerocr.domain.run_spec import RunSpec
from xerocr.evaluation.registry import MetricRegistry, register_default_metrics
from xerocr.evaluation.result import DocumentUsage, RunResult
from xerocr.evaluation.runner import evaluate_run
from xerocr.pipeline.executor import PipelineExecutor, PipelineStepError
from xerocr.pipeline.protocols import Module
from xerocr.pipeline.run_control import RunControl

logger = logging.getLogger(__name__)


class OrchestrationError(XerOCRError):
    """Run impossible à exécuter (document sans image, etc.)."""


#: Sorties d'un run, indexées ``pipeline → document → type → artefact``.
PipelineOutputs = Mapping[str, Mapping[str, Mapping[ArtifactType, Artifact]]]
#: Sink optionnel d'artefacts : reçoit les sorties **avant** le nettoyage du
#: workspace (les URI sont encore lisibles). La couche 6 (app) le fournit ;
#: l'orchestrateur l'invoque sans rien connaître de sa cible (un store, etc.).
ArtifactSink = Callable[[PipelineOutputs, RunManifest], None]
#: Callback de progression : ``(unités traitées, total)``. Émis après chaque
#: document (succès **ou** échec isolé). Une unité = un (concurrent × document).
ProgressCallback = Callable[[int, int], None]


def run(
    spec: RunSpec,
    *,
    registry: ModuleRegistry,
    code_version: str,
    deadline: Deadline | None = None,
    control: RunControl | None = None,
    artifact_sink: ArtifactSink | None = None,
    on_progress: ProgressCallback | None = None,
) -> RunResult:
    """Exécute ``spec`` et renvoie le ``RunResult`` (manifeste + métriques).

    ``control`` (optionnel) porte l'**annulation coopérative** de bout en bout :
    le worker d'un job (``JobRunner``, couche 6) le déclenche, l'exécuteur le
    sonde avant chaque étape. Absent → un ``RunControl`` neutre est utilisé.

    ``artifact_sink`` (optionnel) reçoit les artefacts produits **avant** le
    nettoyage du workspace (URI encore lisibles) : c'est par lui qu'un LAYOUT
    produit est persisté (ex. ``SegmentationStore``) sans que l'orchestrateur
    connaisse la destination, et sans second chemin d'exécution.
    """
    started_at = utcnow()
    needed = sorted(
        {step.adapter_name for pipeline in spec.pipelines for step in pipeline.steps}
    )
    modules = {
        name: registry.build(name, spec.adapter_kwargs.get(name, {}))
        for name in needed
    }
    executor = PipelineExecutor(code_version)
    metric_registry = MetricRegistry()
    register_default_metrics(metric_registry)

    # Workspace temporaire par run : les modules qui produisent des artefacts
    # (tesseract, LLM…) y écrivent ; le runner lit ces sorties avant le nettoyage.
    # Chaque pipeline écrit dans son **propre sous-dossier** : deux pipelines qui
    # partagent un même `adapter_name` (ex. `openai:gpt` corrigeant deux OCR
    # différents) écriraient sinon le même fichier de sortie, et le second
    # écraserait le premier → évaluation contaminée. L'isolation par pipeline
    # tue cette collision sans que les adapters aient à connaître la topologie.
    total_units = len(spec.pipelines) * len(spec.corpus.documents)
    done_units = 0
    with TemporaryDirectory(prefix="xerocr-run-") as workspace:
        pipeline_outputs: dict[str, dict[str, dict[ArtifactType, Artifact]]] = {}
        usage_records: list[DocumentUsage] = []
        for index, pipeline in enumerate(spec.pipelines):
            pipeline_workspace = Path(workspace) / f"pipeline{index}"
            pipeline_workspace.mkdir()
            per_document: dict[str, dict[ArtifactType, Artifact]] = {}
            for document in spec.corpus.documents:
                inputs = _initial_inputs(document)
                try:
                    execution = executor.execute_document(
                        pipeline,
                        modules,
                        inputs,
                        document_id=document.id,
                        deadline=deadline,
                        control=control,
                        workspace_uri=str(pipeline_workspace),
                    )
                    per_document[document.id] = dict(execution.artifacts)
                    usage_records.append(
                        DocumentUsage(
                            document_id=document.id,
                            pipeline=pipeline.name,
                            usage=execution.usage,
                        )
                    )
                except (AdapterStepError, PipelineStepError) as exc:
                    # Un concurrent qui échoue (clé d'API absente, moteur
                    # indisponible, sortie invalide) ne doit PAS abattre tout le
                    # banc d'essai : on **isole** l'échec à ce (concurrent,
                    # document), on journalise, et les autres concurrents restent
                    # exécutés et scorés. Le document non produit n'a pas de
                    # candidat → l'évaluation le laisse simplement non scoré.
                    # L'annulation (`RunCancelledError`, hors de ces classes)
                    # n'est PAS rattrapée : elle arrête bien tout le run.
                    logger.warning(
                        "[orchestrator] concurrent %r · document %r échoué : %s",
                        pipeline.name,
                        document.id,
                        exc,
                    )
                    per_document[document.id] = {}
                done_units += 1
                if on_progress is not None:
                    on_progress(done_units, total_units)
            pipeline_outputs[pipeline.name] = per_document

        completed_at = utcnow()
        manifest = _manifest(
            spec, modules, code_version, started_at, completed_at
        )
        # Sink avant la sortie du ``with`` : les URI des artefacts (LAYOUT…)
        # pointent encore dans le workspace vivant. Best-effort côté appelant.
        if artifact_sink is not None:
            artifact_sink(pipeline_outputs, manifest)
        return evaluate_run(
            corpus=spec.corpus,
            evaluation=spec.evaluation,
            pipeline_outputs=pipeline_outputs,
            registry=metric_registry,
            manifest=manifest,
            usage=tuple(usage_records),
        )


def _initial_inputs(document: DocumentRef) -> dict[ArtifactType, Artifact]:
    if document.image_uri is None:
        raise OrchestrationError(
            f"document {document.id!r} : image_uri requis (axe image→texte)."
        )
    return {
        ArtifactType.IMAGE: Artifact(
            id=f"{document.id}:initial:image",
            document_id=document.id,
            type=ArtifactType.IMAGE,
            uri=document.image_uri,
        )
    }


def _manifest(
    spec: RunSpec,
    modules: Mapping[str, Module],
    code_version: str,
    started_at: datetime,
    completed_at: datetime,
) -> RunManifest:
    names = sorted(modules)
    return RunManifest(
        run_id=spec.run_id or f"run-{started_at.strftime('%Y%m%dT%H%M%S')}",
        corpus_name=spec.corpus.name,
        n_documents=len(spec.corpus.documents),
        pipeline_specs=spec.pipelines,
        adapter_kwargs={
            name: dict(spec.adapter_kwargs.get(name, {})) for name in names
        },
        # Reproductibilité (R-2) : la version de chaque module exécuté entre dans
        # l'empreinte. La version *binaire* d'un moteur externe (ex. tesseract)
        # reste à capturer dans `system_binaries_lock` à l'exécution (appel live,
        # hors CI) — non couvert ici : `module.version` est la version d'adapter.
        module_versions={name: modules[name].version for name in names},
        view_specs=spec.evaluation.views,
        code_version=code_version,
        started_at=started_at,
        completed_at=completed_at,
        metadata=spec.metadata,
    )


__all__ = ["ArtifactSink", "OrchestrationError", "PipelineOutputs", "run"]
