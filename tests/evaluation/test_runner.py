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
from xerocr.evaluation.result import RunResult
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
    # micro = Σ erreurs / Σ longueurs = (1 + 0) / (4 + 2) = 1/6, PAS la moyenne
    # macro mean(0.25, 0.0) = 0.125 : un long document pèse plus (cf. _aggregate).
    assert aggregate.value == pytest.approx(1 / 6)
    assert len(result.documents) == 2
    # le détail par-document porte le poids (dénominateur) → macro reconstructible.
    doc1_cer = result.documents[0].scores[0]
    assert doc1_cer.value == pytest.approx(0.25)
    assert doc1_cer.support == 4  # longueur de la référence "abcd"


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


def test_candidate_precedence_prefers_corrected(tmp_path: Path) -> None:
    # Vue à 2 candidats : la précédence EXPLICITE choisit CORRECTED_TEXT (aval),
    # pas l'ordre alphabétique des valeurs d'enum.
    gt = _write(tmp_path / "d.gt.txt", "alpha")
    raw = _write(tmp_path / "d.raw.txt", "beta")  # CER > 0 si choisi
    corrected = _write(tmp_path / "d.corr.txt", "alpha")  # CER 0 si choisi
    corpus = CorpusSpec(name="c", documents=(_doc("d", gt),))
    view = EvaluationView(
        name="multi",
        candidate_types=frozenset(
            {ArtifactType.RAW_TEXT, ArtifactType.CORRECTED_TEXT}
        ),
        metric_names=("cer",),
    )
    outputs = {
        "eng": {
            "d": {
                ArtifactType.RAW_TEXT: _candidate("d", raw),
                ArtifactType.CORRECTED_TEXT: Artifact(
                    id="d:llm:corrected_text",
                    document_id="d",
                    type=ArtifactType.CORRECTED_TEXT,
                    uri=str(corrected),
                ),
            }
        }
    }
    result = evaluate_run(
        corpus=corpus,
        evaluation=EvaluationSpec(views=(view,)),
        pipeline_outputs=outputs,
        registry=_registry(),
        manifest=_manifest(1),
    )
    assert result.pipelines[0].aggregate[0].value == 0.0  # CORRECTED choisi


def test_cross_engine_significance_written(tmp_path: Path) -> None:
    # 2 pipelines (a parfait, b avec erreurs) → RunResult.cross_engine peuplé
    gt1 = _write(tmp_path / "d1.gt.txt", "abcd")
    gt2 = _write(tmp_path / "d2.gt.txt", "abcd")
    a1 = _write(tmp_path / "d1.a.txt", "abcd")
    a2 = _write(tmp_path / "d2.a.txt", "abcd")
    b1 = _write(tmp_path / "d1.b.txt", "xbcd")
    b2 = _write(tmp_path / "d2.b.txt", "xycd")
    corpus = CorpusSpec(name="c", documents=(_doc("d1", gt1), _doc("d2", gt2)))
    manifest = RunManifest(
        run_id="r",
        corpus_name="c",
        n_documents=2,
        pipeline_specs=(
            PipelineSpec(name="a", initial_inputs=(ArtifactType.IMAGE,)),
            PipelineSpec(name="b", initial_inputs=(ArtifactType.IMAGE,)),
        ),
        code_version="1.0",
        started_at=FIXED,
        completed_at=FIXED,
    )
    outputs = {
        "a": {
            "d1": {ArtifactType.RAW_TEXT: _candidate("d1", a1)},
            "d2": {ArtifactType.RAW_TEXT: _candidate("d2", a2)},
        },
        "b": {
            "d1": {ArtifactType.RAW_TEXT: _candidate("d1", b1)},
            "d2": {ArtifactType.RAW_TEXT: _candidate("d2", b2)},
        },
    }
    result = evaluate_run(
        corpus=corpus,
        evaluation=EvaluationSpec(views=(TEXT_VIEW,)),
        pipeline_outputs=outputs,
        registry=_registry(),
        manifest=manifest,
    )
    keys = {score.metric for score in result.cross_engine}
    assert "text:cer:significance_p" in keys


def test_inference_analyses_through_evaluate_run(tmp_path: Path) -> None:
    """≥6 docs × 3 pipelines → le runner produit le payload ``inference``."""
    gt_texts = ["abcdefgh", "ijklmnop", "qrstuvwx", "yzabcdef", "ghijklmn", "opqrstuv"]
    # alpha = parfait ; beta = 2 erreurs/doc ; gamma = 1 erreur/doc.
    documents = []
    outputs: dict[str, dict[str, dict[ArtifactType, Artifact]]] = {
        "alpha": {}, "beta": {}, "gamma": {},
    }
    for i, text in enumerate(gt_texts):
        doc_id = f"d{i}"
        gt = _write(tmp_path / f"{doc_id}.gt.txt", text)
        documents.append(_doc(doc_id, gt))
        for name, hyp in (
            ("alpha", text),
            ("beta", "XY" + text[2:]),
            ("gamma", "X" + text[1:]),
        ):
            path = _write(tmp_path / f"{doc_id}.{name}.txt", hyp)
            outputs[name][doc_id] = {
                ArtifactType.RAW_TEXT: _candidate(doc_id, path)
            }
    corpus = CorpusSpec(name="c", documents=tuple(documents))
    manifest = RunManifest(
        run_id="r",
        corpus_name="c",
        n_documents=6,
        pipeline_specs=tuple(
            PipelineSpec(name=n, initial_inputs=(ArtifactType.IMAGE,))
            for n in ("alpha", "beta", "gamma")
        ),
        code_version="1.0",
        started_at=FIXED,
        completed_at=FIXED,
    )
    result = evaluate_run(
        corpus=corpus,
        evaluation=EvaluationSpec(views=(TEXT_VIEW,)),
        pipeline_outputs=outputs,
        registry=_registry(),
        manifest=manifest,
    )
    by_kind = {a.payload.kind: a for a in result.analyses}
    assert set(by_kind) == {
        "inference",
        "diagnostics",
        "taxonomy",
        "document_texts",
        "textual_fidelity",
        "inter_engine",
        "lines",
    }
    analysis = by_kind["inference"]
    assert analysis.view == "text" and analysis.scope == "corpus"
    payload = analysis.payload
    assert payload.kind == "inference" and payload.metric == "cer"
    # Le diagnostic voit les mêmes textes : beta (2 erreurs/doc) produit des
    # confusions X→i/j/q/y..., et les documents sont classés par CER moyen.
    diagnostics = by_kind["diagnostics"].payload
    assert diagnostics.confusions and diagnostics.hardest_documents
    assert diagnostics.worst_lines[0].cer > 0
    # Taxonomie : beta remplace les 2 premiers chars (« XY... » : substitution
    # résiduelle), gamma 1 char — classes comptées par règles pures.
    taxonomy = by_kind["taxonomy"].payload
    assert {row.pipeline for row in taxonomy.pipelines} == {"beta", "gamma"}
    assert all(row.total_errors > 0 for row in taxonomy.pipelines)
    # Inter-moteurs : alpha rattrape tous les tokens (oracle = parfait = 1.0,
    # gap nul) ; beta/gamma remplacent le seul mot de chaque doc → profils
    # taxonomy identiques ({other}) → divergence à 0, pas de paire max.
    inter_engine = by_kind["inter_engine"].payload
    comp = inter_engine.complementarity
    assert comp is not None and comp.n_documents == 6
    assert comp.best_engine == "alpha"
    assert comp.oracle_recall == 1.0 and comp.absolute_gap == 0.0
    divergence = inter_engine.taxonomy_divergence
    assert divergence is not None
    assert [(p.a, p.b) for p in divergence.pairs] == [("beta", "gamma")]
    assert divergence.pairs[0].divergence == 0.0
    assert divergence.max_pair is None
    # Lignes (vue sans profil → sauts de ligne préservés) : 1 ligne par doc,
    # CER ligne = CER doc — beta 2/8, gamma 1/8, alpha parfait.
    lines = by_kind["lines"].payload
    by_pipeline = {row.pipeline: row for row in lines.pipelines}
    assert set(by_pipeline) == {"alpha", "beta", "gamma"}
    assert all(row.line_count == 6 for row in lines.pipelines)
    assert by_pipeline["alpha"].mean_cer == 0.0
    assert by_pipeline["beta"].mean_cer == 0.25
    assert by_pipeline["gamma"].mean_cer == 0.125
    assert by_pipeline["beta"].gini == 0.0  # erreurs uniformes (0.25 partout)
    assert payload.n_documents == 6
    assert payload.critical_distance is not None  # 3 pipelines → post-hoc
    assert [r.pipeline for r in payload.mean_ranks] == ["alpha", "gamma", "beta"]
    # Round-trip JSON : le payload structuré survit tel quel.
    reloaded = RunResult.model_validate_json(result.model_dump_json())
    assert reloaded.analyses == result.analyses
