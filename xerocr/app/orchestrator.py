"""Orchestrateur de run (couche 6) — **coquille mince qui ne calcule pas**.

Câble les couches internes : construit les modules (registre), fait tourner
l'exécuteur (couche 4) par document, passe les artefacts au runner d'évaluation
(couche 3), assemble le ``RunResult`` + le ``RunManifest``. Il **n'évalue rien
lui-même** (l'assemblage métrique vit en ``evaluation``) et **n'exécute aucun
moteur** (les modules le font).

Minimal pour T1 : mono-thread, séquentiel. Le ``JobRunner`` (annulation/SSE), le
loader YAML et la sécurité des chemins arrivent à leurs tranches (T2/T4).
"""

from __future__ import annotations

from datetime import datetime
from tempfile import TemporaryDirectory

from xerocr.app.modules.registry import ModuleRegistry
from xerocr.domain.artifacts import Artifact, ArtifactType
from xerocr.domain.deadline import Deadline
from xerocr.domain.documents import DocumentRef
from xerocr.domain.errors import XerOCRError
from xerocr.domain.run import RunManifest, utcnow
from xerocr.domain.run_spec import RunSpec
from xerocr.evaluation.registry import MetricRegistry, register_default_metrics
from xerocr.evaluation.result import RunResult
from xerocr.evaluation.runner import evaluate_run
from xerocr.pipeline.executor import PipelineExecutor


class OrchestrationError(XerOCRError):
    """Run impossible à exécuter (document sans image, etc.)."""


def run(
    spec: RunSpec,
    *,
    registry: ModuleRegistry,
    code_version: str,
    deadline: Deadline | None = None,
) -> RunResult:
    """Exécute ``spec`` et renvoie le ``RunResult`` (manifeste + métriques)."""
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
    # (tesseract…) y écrivent ; le runner lit ces sorties avant le nettoyage.
    with TemporaryDirectory(prefix="xerocr-run-") as workspace:
        pipeline_outputs: dict[str, dict[str, dict[ArtifactType, Artifact]]] = {}
        for pipeline in spec.pipelines:
            per_document: dict[str, dict[ArtifactType, Artifact]] = {}
            for document in spec.corpus.documents:
                per_document[document.id] = executor.execute_document(
                    pipeline,
                    modules,
                    _initial_inputs(document),
                    document_id=document.id,
                    deadline=deadline,
                    workspace_uri=workspace,
                )
            pipeline_outputs[pipeline.name] = per_document

        completed_at = utcnow()
        manifest = _manifest(spec, needed, code_version, started_at, completed_at)
        return evaluate_run(
            corpus=spec.corpus,
            evaluation=spec.evaluation,
            pipeline_outputs=pipeline_outputs,
            registry=metric_registry,
            manifest=manifest,
        )


def _initial_inputs(document: DocumentRef) -> dict[ArtifactType, Artifact]:
    if document.image_uri is None:
        raise OrchestrationError(
            f"document {document.id!r} : image_uri requis (T1, axe image→texte)."
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
    needed: list[str],
    code_version: str,
    started_at: datetime,
    completed_at: datetime,
) -> RunManifest:
    return RunManifest(
        run_id=spec.run_id or f"run-{started_at.strftime('%Y%m%dT%H%M%S')}",
        corpus_name=spec.corpus.name,
        n_documents=len(spec.corpus.documents),
        pipeline_specs=spec.pipelines,
        adapter_kwargs={
            name: dict(spec.adapter_kwargs.get(name, {})) for name in needed
        },
        view_specs=spec.evaluation.views,
        code_version=code_version,
        started_at=started_at,
        completed_at=completed_at,
        metadata=spec.metadata,
    )


__all__ = ["OrchestrationError", "run"]
