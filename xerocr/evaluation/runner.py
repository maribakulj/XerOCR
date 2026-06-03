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
from xerocr.domain.documents import DocumentRef, GroundTruthRef
from xerocr.domain.evaluation import EvaluationSpec, EvaluationView
from xerocr.domain.run import RunManifest
from xerocr.evaluation.context import CrossEngineContext, DocContext
from xerocr.evaluation.errors import EvaluationError
from xerocr.evaluation.projectors import get_projector
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

#: Précédence **explicite** de sélection du candidat quand une vue déclare
#: plusieurs ``candidate_types`` : du plus **aval** (corrigé) au plus brut — on
#: évalue la sortie la plus aboutie du pipeline. Jamais l'ordre alphabétique des
#: valeurs d'enum (qui ne coïncide avec l'intention que par hasard).
_CANDIDATE_PRECEDENCE: tuple[ArtifactType, ...] = (
    ArtifactType.CORRECTED_TEXT,
    ArtifactType.RAW_TEXT,
)

#: { métrique : { pipeline : [score par doc, aligné, ``None`` inclus] } }
_Series = dict[str, dict[str, list[MetricScore]]]

#: Types **inter-changeables au niveau représentation** : tous chargés en ``str``.
#: Un candidat ``CORRECTED_TEXT`` est donc noté par une métrique ``RAW_TEXT`` sans
#: projection (les post-corrections LLM, comportement T3 préservé).
_TEXT_LIKE = frozenset({ArtifactType.RAW_TEXT, ArtifactType.CORRECTED_TEXT})


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
                    series[score.metric][pipeline_name].append(score)
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


def _aggregate(name: str, scores: list[MetricScore]) -> MetricScore:
    """Agrégat **micro** : Σ(valeur·poids)/Σpoids — la métrique au niveau corpus.

    Micro (et non la moyenne *macro* des taux par-document) est la métrique
    conventionnelle au niveau corpus, comparable à ``jiwer`` sur le corpus
    entier : un long document pèse à proportion de sa taille. La moyenne macro
    reste reconstructible depuis le détail par-document (``RunResult.documents``).
    Les documents à poids nul (référence vide) sont exclus du micro ; ``value``
    vaut ``None`` si aucun poids (toutes réfs vides). ``support`` = nombre de
    documents applicables.
    """
    pairs: list[tuple[float, int]] = []
    for score in scores:
        if score.value is not None:
            pairs.append((score.value, score.support or 0))
    total_weight = sum(weight for _, weight in pairs)
    micro = (
        sum(value * weight for value, weight in pairs) / total_weight
        if total_weight > 0
        else None
    )
    return MetricScore(metric=name, value=micro, support=len(pairs))


def _cross_engine_scores(
    view: EvaluationView, series: _Series, registry: MetricRegistry
) -> list[MetricScore]:
    metrics = registry.cross_engine_metrics()
    if not metrics:
        return []
    scores: list[MetricScore] = []
    for base_metric in view.metric_names:
        per_pipeline = {
            pipeline: tuple(score.value for score in scores_list)
            for pipeline, scores_list in series[base_metric].items()
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
    ordered = [t for t in _CANDIDATE_PRECEDENCE if t in candidate_types]
    ordered.extend(
        sorted(
            (t for t in candidate_types if t not in _CANDIDATE_PRECEDENCE),
            key=lambda t: t.value,
        )
    )
    for artifact_type in ordered:
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
        observation = metric.fn(context) if context is not None else None
        scores.append(
            MetricScore(
                metric=name,
                value=observation.value if observation is not None else None,
                support=observation.weight if observation is not None else None,
            )
        )
    return tuple(scores)


def _context_for(
    view: EvaluationView,
    document: DocumentRef,
    candidate: Artifact | None,
    signature: _Signature,
) -> DocContext | None:
    reference_type, hypothesis_type = signature
    if candidate is None or candidate.uri is None:
        return None
    resolved = _resolve_ground_truth(document, view, reference_type)
    if resolved is None:
        return None
    ground_truth, gt_native_type = resolved
    reference = _project_side(ground_truth.uri, gt_native_type, reference_type, view)
    hypothesis = _project_side(candidate.uri, candidate.type, hypothesis_type, view)
    if reference is None or hypothesis is None:
        return None
    return DocContext(
        document_id=document.id,
        reference=_prepare(reference, view),
        hypothesis=_prepare(hypothesis, view),
    )


def _resolve_ground_truth(
    document: DocumentRef, view: EvaluationView, reference_type: ArtifactType
) -> tuple[GroundTruthRef, ArtifactType] | None:
    """GT dont le type natif **alimente** ``reference_type`` (direct ou projeté)."""
    direct = document.gt_for(reference_type)
    if direct is not None:
        return direct, reference_type
    for gt in document.ground_truths:
        spec = view.projection_for(gt.type)
        if spec is not None and spec.target_type == reference_type:
            return gt, gt.type
    return None


def _project_side(
    uri: str,
    native_type: ArtifactType,
    target_type: ArtifactType,
    view: EvaluationView,
) -> object | None:
    """Charge ``uri`` dans son type natif, projette vers ``target_type`` si besoin.

    Identité si types égaux ou tous deux *text-like* (même représentation ``str``).
    Sinon une ``ProjectionSpec`` de la vue doit pont(er) ``native → target`` ; à
    défaut, ``None`` (jonction non applicable, pas de comparaison factice).
    """
    representation = load_representation(uri, native_type)
    if native_type == target_type or (
        native_type in _TEXT_LIKE and target_type in _TEXT_LIKE
    ):
        return representation
    spec = view.projection_for(native_type)
    if spec is None or spec.target_type != target_type:
        return None
    return get_projector(spec.projector_name)(representation, spec.params)


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
