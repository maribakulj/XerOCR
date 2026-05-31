"""``evaluate_run`` — le runner (par-document → agrégat → inter-moteurs).

Reçoit des **artefacts déjà produits** (couche 4, via l'app) : il n'exécute aucun
moteur et n'importe pas ``pipeline``. **Trois passes** par vue : (1) par-document
(``None`` = non applicable), (2) agrégat par pipeline (``None`` exclu, **support**
exposé), (3) **inter-moteurs** — chaque ``CrossEngineMetric`` compare les
pipelines et écrit dans ``RunResult.cross_engine``.

Normalisation de la vue (``normalization_profile``/``char_exclude``) appliquée
symétriquement GT/hyp ; représentation chargée+normalisée **une fois par
signature** ``(ref, hyp)``.
"""

from __future__ import annotations

from collections.abc import Mapping

from xerocr.domain.artifacts import Artifact, ArtifactType
from xerocr.domain.corpus import CorpusSpec
from xerocr.domain.documents import DocumentRef
from xerocr.domain.evaluation import EvaluationSpec, EvaluationView
from xerocr.domain.run import RunManifest
from xerocr.evaluation.context import CrossEngineContext, DocContext
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
from xerocr.formats.text import get_builtin_profile

#: { pipeline_name: { document_id: { ArtifactType: Artifact } } }
PipelineOutputs = Mapping[str, Mapping[str, Mapping[ArtifactType, Artifact]]]

#: Signature d'entrée d'une métrique : ``(type_référence, type_hypothèse)``.
_Signature = tuple[ArtifactType, ArtifactType]

#: { métrique : { pipeline : [valeur par doc, alignée, ``None`` inclus] } }
_Series = dict[str, dict[str, list[float | None]]]


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
    cross_engine: list[MetricScore] = []

    for view in evaluation.views:
        series: _Series = {name: {} for name in view.metric_names}
        for pipeline_name in pipeline_order:
            for name in view.metric_names:
                series[name][pipeline_name] = []
            for document in corpus.documents:
                candidate = _candidate_for(
                    pipeline_outputs, pipeline_name, document.id, view.candidate_types
                )
                scores = _score_document(view, document, candidate, registry)
                for score in scores:
                    series[score.metric][pipeline_name].append(score.value)
                documents.append(
                    RunDocumentResult(
                        document_id=document.id,
                        pipeline=pipeline_name,
                        view=view.name,
                        scores=scores,
                    )
                )
            pipelines.append(
                PipelineResult(
                    pipeline=pipeline_name,
                    view=view.name,
                    aggregate=tuple(
                        _aggregate(name, series[name][pipeline_name])
                        for name in view.metric_names
                    ),
                )
            )
        cross_engine.extend(_cross_engine_scores(view, series, registry))

    return RunResult(
        manifest=manifest,
        pipelines=tuple(pipelines),
        documents=tuple(documents),
        cross_engine=tuple(cross_engine),
    )


def _aggregate(name: str, values: list[float | None]) -> MetricScore:
    present = [value for value in values if value is not None]
    return MetricScore(metric=name, value=safe_mean(present), support=len(present))


def _cross_engine_scores(
    view: EvaluationView, series: _Series, registry: MetricRegistry
) -> list[MetricScore]:
    metrics = registry.cross_engine_metrics()
    if not metrics:
        return []
    scores: list[MetricScore] = []
    for base_metric in view.metric_names:
        per_pipeline = {
            pipeline: tuple(values)
            for pipeline, values in series[base_metric].items()
        }
        context = CrossEngineContext(metric=base_metric, per_pipeline=per_pipeline)
        for metric in metrics:
            value, support = metric.fn(context)
            scores.append(
                MetricScore(
                    metric=f"{view.name}:{base_metric}:{metric.name}",
                    value=value,
                    support=support,
                )
            )
    return scores


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
) -> tuple[MetricScore, ...]:
    # Représentation chargée + normalisée une seule fois par signature, partagée
    # par toutes les métriques qui la consomment (CER/WER/MER).
    contexts: dict[_Signature, DocContext | None] = {}
    scores: list[MetricScore] = []
    for name in view.metric_names:
        metric = registry.document_metric(name)
        if metric is None:
            raise EvaluationError(f"métrique inconnue : {name!r}.")
        signature = metric.input_types
        if signature not in contexts:
            contexts[signature] = _context_for(view, document, candidate, signature)
        context = contexts[signature]
        value = metric.fn(context) if context is not None else None
        scores.append(MetricScore(metric=name, value=value))
    return tuple(scores)


def _context_for(
    view: EvaluationView,
    document: DocumentRef,
    candidate: Artifact | None,
    signature: _Signature,
) -> DocContext | None:
    reference_type, hypothesis_type = signature
    ground_truth = document.gt_for(reference_type)
    if candidate is None or candidate.uri is None or ground_truth is None:
        return None
    reference = _prepare(load_representation(ground_truth.uri, reference_type), view)
    hypothesis = _prepare(load_representation(candidate.uri, hypothesis_type), view)
    return DocContext(
        document_id=document.id, reference=reference, hypothesis=hypothesis
    )


def _prepare(representation: object, view: EvaluationView) -> object:
    """Applique la normalisation de la vue (profil + ``char_exclude``) au texte."""
    if not isinstance(representation, str):
        return representation
    text = representation
    if view.normalization_profile is not None:
        try:
            profile = get_builtin_profile(view.normalization_profile)
        except KeyError as exc:
            raise EvaluationError(str(exc)) from exc
        text = profile.normalize(text)
    if view.char_exclude:
        excluded = set(view.char_exclude)
        text = "".join(char for char in text if char not in excluded)
    return text


__all__ = ["PipelineOutputs", "evaluate_run"]
