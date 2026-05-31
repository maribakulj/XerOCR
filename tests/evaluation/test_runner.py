"""Runner d'évaluation : agrégat + détail par-document, ``None`` si non applicable."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from xerocr.domain.artifacts import Artifact, ArtifactType
from xerocr.domain.corpus import CorpusSpec
from xerocr.domain.documents import DocumentRef, GroundTruthRef
from xerocr.domain.evaluation import EvaluationSpec, EvaluationView
from xerocr.domain.pipeline import PipelineSpec
from xerocr.domain.run import RunManifest
from xerocr.evaluation.errors import EvaluationError
from xerocr.evaluation.registry import MetricRegistry, register_default_metrics
from xerocr.evaluation.runner import evaluate_run

FIXED = datetime(2026, 1, 1, tzinfo=UTC)
TEXT_VIEW = EvaluationView(
    name="text",
    candidate_types=frozenset({ArtifactType.RAW_TEXT}),
    metric_names=("cer",),
)


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def _doc(doc_id: str, gt: Path | None) -> DocumentRef:
    truths = ()
    if gt is not None:
        truths = (GroundTruthRef(type=ArtifactType.RAW_TEXT, uri=str(gt)),)
    return DocumentRef(id=doc_id, ground_truths=truths)


def _candidate(document_id: str, uri: Path) -> Artifact:
    return Artifact(
        id=f"{document_id}:precomputed:raw_text",
        document_id=document_id,
        type=ArtifactType.RAW_TEXT,
        uri=str(uri),
    )


def _manifest(n: int) -> RunManifest:
    pipeline = PipelineSpec(name="eng", initial_inputs=(ArtifactType.IMAGE,))
    return RunManifest(
        run_id="r",
        corpus_name="c",
        n_documents=n,
        pipeline_specs=(pipeline,),
        code_version="1.0",
        started_at=FIXED,
        completed_at=FIXED,
    )


def _registry() -> MetricRegistry:
    registry = MetricRegistry()
    register_default_metrics(registry)
    return registry


def test_aggregate_and_per_document(tmp_path: Path) -> None:
    # doc1 : GT "abcd" vs "abxd" -> CER 1/4 ; doc2 : GT "ef" vs "ef" -> 0
    gt1 = _write(tmp_path / "doc1.gt.txt", "abcd")
    hyp1 = _write(tmp_path / "doc1.eng.txt", "abxd")
    gt2 = _write(tmp_path / "doc2.gt.txt", "ef")
    hyp2 = _write(tmp_path / "doc2.eng.txt", "ef")
    corpus = CorpusSpec(name="c", documents=(_doc("doc1", gt1), _doc("doc2", gt2)))
    outputs = {
        "eng": {
            "doc1": {ArtifactType.RAW_TEXT: _candidate("doc1", hyp1)},
            "doc2": {ArtifactType.RAW_TEXT: _candidate("doc2", hyp2)},
        }
    }
    result = evaluate_run(
        corpus=corpus,
        evaluation=EvaluationSpec(views=(TEXT_VIEW,)),
        pipeline_outputs=outputs,
        registry=_registry(),
        manifest=_manifest(2),
    )
    aggregate = result.pipelines[0].aggregate[0]
    assert aggregate.metric == "cer"
    assert aggregate.support == 2
    assert aggregate.value == pytest.approx(0.125)  # mean(0.25, 0.0)
    assert len(result.documents) == 2


def test_missing_ground_truth_is_not_applicable(tmp_path: Path) -> None:
    hyp1 = _write(tmp_path / "doc1.eng.txt", "abc")
    corpus = CorpusSpec(name="c", documents=(_doc("doc1", None),))
    outputs = {"eng": {"doc1": {ArtifactType.RAW_TEXT: _candidate("doc1", hyp1)}}}
    result = evaluate_run(
        corpus=corpus,
        evaluation=EvaluationSpec(views=(TEXT_VIEW,)),
        pipeline_outputs=outputs,
        registry=_registry(),
        manifest=_manifest(1),
    )
    aggregate = result.pipelines[0].aggregate[0]
    assert aggregate.value is None
    assert aggregate.support == 0
    assert result.documents[0].scores[0].value is None


def test_normalization_profile_neutralises_case(tmp_path: Path) -> None:
    # vue "caseless" : "ABC DEF" (GT) vs "abc def" (hyp) → CER 0 (casse neutralisée)
    gt = _write(tmp_path / "doc1.gt.txt", "ABC DEF")
    hyp = _write(tmp_path / "doc1.eng.txt", "abc def")
    corpus = CorpusSpec(name="c", documents=(_doc("doc1", gt),))
    view = EvaluationView(
        name="caseless",
        candidate_types=frozenset({ArtifactType.RAW_TEXT}),
        metric_names=("cer",),
        normalization_profile="caseless",
    )
    outputs = {"eng": {"doc1": {ArtifactType.RAW_TEXT: _candidate("doc1", hyp)}}}
    result = evaluate_run(
        corpus=corpus,
        evaluation=EvaluationSpec(views=(view,)),
        pipeline_outputs=outputs,
        registry=_registry(),
        manifest=_manifest(1),
    )
    assert result.pipelines[0].aggregate[0].value == 0.0


def test_unknown_normalization_profile_raises(tmp_path: Path) -> None:
    gt = _write(tmp_path / "doc1.gt.txt", "x")
    hyp = _write(tmp_path / "doc1.eng.txt", "x")
    corpus = CorpusSpec(name="c", documents=(_doc("doc1", gt),))
    view = EvaluationView(
        name="bad",
        candidate_types=frozenset({ArtifactType.RAW_TEXT}),
        metric_names=("cer",),
        normalization_profile="does_not_exist",
    )
    outputs = {"eng": {"doc1": {ArtifactType.RAW_TEXT: _candidate("doc1", hyp)}}}
    with pytest.raises(EvaluationError):
        evaluate_run(
            corpus=corpus,
            evaluation=EvaluationSpec(views=(view,)),
            pipeline_outputs=outputs,
            registry=_registry(),
            manifest=_manifest(1),
        )
