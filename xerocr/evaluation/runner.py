"""``evaluate_run`` — le runner d'évaluation (par-document → agrégat).

Reçoit des **artefacts déjà produits** (par l'exécuteur de la couche 4, via
l'app) : il n'exécute aucun moteur et n'importe pas ``pipeline`` (couche plus
externe). Deux passes : (1) par-document, ``None`` = non applicable ; (2) agrégat
par pipeline, ``None`` **exclu**, **support** exposé. La passe inter-moteurs
(``cross_engine``) arrive en T2.
"""

from __future__ import annotations

from collections.abc import Mapping

from xerocr.domain.artifacts import Artifact, ArtifactType
from xerocr.domain.corpus import CorpusSpec
from xerocr.domain.documents import DocumentRef
from xerocr.domain.evaluation import EvaluationSpec, EvaluationView
from xerocr.domain.run import RunManifest
from xerocr.evaluation.context import DocContext
from xerocr.evaluation.errors import EvaluationError
from xerocr.evaluation.metrics._helpers import safe_mean
from xerocr.evaluation.registry import MetricRegistry
from xerocr.evaluation.representations import load_representation
from xerocr.evaluation.result import (
    MetricScore,
    PipelineResult,
    RunDocumentResult,
    RunResult,
)

#: { pipeline_name: { document_id: { ArtifactType: Artifact } } }
PipelineOutputs = Mapping[str, Mapping[str, Mapping[ArtifactType, Artifact]]]


def evaluate_run(
    *,
    corpus: CorpusSpec,
    evaluation: EvaluationSpec,
    pipeline_outputs: PipelineOutputs,
    registry: MetricRegistry,
    manifest: RunManifest,
) -> RunResult:
    """Calcule le ``RunResult`` depuis les sorties de pipelines et la GT."""
    pipeline_order = [spec.name for spec in manifest.pipeline_specs]
    pipelines: list[PipelineResult] = []
    documents: list[RunDocumentResult] = []

    for view in evaluation.views:
        for pipeline_name in pipeline_order:
            collected: dict[str, list[float]] = {n: [] for n in view.metric_names}
            for document in corpus.documents:
                candidate = _candidate_for(
                    pipeline_outputs, pipeline_name, document.id, view.candidate_types
                )
                scores = _score_document(view, document, candidate, registry, collected)
                documents.append(
                    RunDocumentResult(
                        document_id=document.id,
                        pipeline=pipeline_name,
                        view=view.name,
                        scores=scores,
                    )
                )
            aggregate = tuple(
                MetricScore(
                    metric=name,
                    value=safe_mean(collected[name]),
                    support=len(collected[name]),
                )
                for name in view.metric_names
            )
            pipelines.append(
                PipelineResult(
                    pipeline=pipeline_name, view=view.name, aggregate=aggregate
                )
            )

    return RunResult(
        manifest=manifest, pipelines=tuple(pipelines), documents=tuple(documents)
    )


def _candidate_for(
    pipeline_outputs: PipelineOutputs,
    pipeline_name: str,
    document_id: str,
    candidate_types: frozenset[ArtifactType],
) -> Artifact | None:
    by_document: Mapping[str, Mapping[ArtifactType, Artifact]] = (
        pipeline_outputs.get(pipeline_name, {})
    )
    outputs: Mapping[ArtifactType, Artifact] = by_document.get(document_id, {})
    for artifact_type in sorted(candidate_types, key=lambda t: t.value):
        if artifact_type in outputs:
            return outputs[artifact_type]
    return None


def _score_document(
    view: EvaluationView,
    document: DocumentRef,
    candidate: Artifact | None,
    registry: MetricRegistry,
    collected: dict[str, list[float]],
) -> tuple[MetricScore, ...]:
    scores: list[MetricScore] = []
    for name in view.metric_names:
        metric = registry.document_metric(name)
        if metric is None:
            raise EvaluationError(f"métrique inconnue : {name!r}.")
        reference_type, hypothesis_type = metric.input_types
        ground_truth = document.gt_for(reference_type)
        value: float | None
        if candidate is None or candidate.uri is None or ground_truth is None:
            value = None
        else:
            value = metric.fn(
                DocContext(
                    document_id=document.id,
                    reference=load_representation(ground_truth.uri, reference_type),
                    hypothesis=load_representation(candidate.uri, hypothesis_type),
                )
            )
        if value is not None:
            collected[name].append(value)
        scores.append(MetricScore(metric=name, value=value))
    return tuple(scores)


__all__ = ["PipelineOutputs", "evaluate_run"]
