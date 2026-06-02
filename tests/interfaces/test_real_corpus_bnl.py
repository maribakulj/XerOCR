"""Benchmark XerOCR sur **données réelles** : corpus BNL (presse historique
luxembourgeoise, **multilingue** allemand Fraktur + français), 4 pipelines
Tesseract — ``frk`` (Fraktur legacy) · ``deu`` (allemand moderne) · ``fra``
(français) · ``deu_latf`` (Fraktur LSTM « best »).

Déterministe en CI : la GT (extraite des ALTO v4 BNL) et les sorties OCR sont
**figées** dans ``tests/fixtures/reference_corpus/bnl_mini/`` ; on les rejoue via
l'adapter ``precomputed`` (aucun Tesseract requis en CI). Vérifie ce que le
synthétique ne pouvait pas : de **vraies** métriques **et** une **significativité
inter-moteurs vivante** (n≈30 ≥ plancher de puissance 6, ≠ démo n=3 → ``None``).
"""

from __future__ import annotations

import shutil
from pathlib import Path

from xerocr.app import resolve_code_version
from xerocr.app import run as run_orchestrator
from xerocr.app.modules.registry import ModuleRegistry, register_default_modules
from xerocr.domain.artifacts import ArtifactType
from xerocr.domain.corpus import CorpusSpec
from xerocr.domain.documents import DocumentRef, GroundTruthRef
from xerocr.domain.evaluation import EvaluationSpec, EvaluationView
from xerocr.domain.pipeline import PipelineSpec, PipelineStep
from xerocr.domain.run_spec import RunSpec
from xerocr.evaluation.result import RunResult
from xerocr.reports import default_report_renderer

_FIXTURES = (
    Path(__file__).resolve().parent.parent
    / "fixtures"
    / "reference_corpus"
    / "bnl_mini"
)
#: Documents découverts depuis la fixture (la GT figée fait foi).
_DOC_IDS = tuple(sorted(p.name.removesuffix(".gt.txt") for p in _FIXTURES.glob("*.gt.txt")))
#: 4 pipelines Tesseract : Fraktur legacy · allemand moderne · français · Fraktur LSTM.
_ENGINES = ("frk", "deu", "fra", "deu_latf")


def _document(root: Path, doc_id: str) -> DocumentRef:
    return DocumentRef(
        id=doc_id,
        image_uri=str(root / f"{doc_id}.png"),  # absent, ignoré par precomputed
        ground_truths=(
            GroundTruthRef(
                type=ArtifactType.RAW_TEXT,
                uri=str(root / f"{doc_id}.gt.txt"),
            ),
        ),
    )


def _pipeline(label: str) -> PipelineSpec:
    return PipelineSpec(
        name=label,
        initial_inputs=(ArtifactType.IMAGE,),
        steps=(
            PipelineStep(
                id="ocr",
                kind="ocr",
                adapter_name=f"precomputed:{label}",
                input_types=(ArtifactType.IMAGE,),
                output_types=(ArtifactType.RAW_TEXT,),
            ),
        ),
    )


def build_bnl_run_result(root: Path) -> RunResult:
    """Matérialise le corpus BNL figé dans ``root`` et exécute le run (precomputed)."""
    for doc_id in _DOC_IDS:
        for suffix in ("gt", *_ENGINES):
            name = f"{doc_id}.{suffix}.txt"
            shutil.copy(_FIXTURES / name, root / name)
    corpus = CorpusSpec(
        name="bnl_mini",
        documents=tuple(_document(root, doc_id) for doc_id in _DOC_IDS),
        metadata={"source": "BNL", "languages": "deu,fra", "script": "fraktur+antiqua"},
    )
    views = (
        EvaluationView(
            name="text",
            candidate_types=frozenset({ArtifactType.RAW_TEXT}),
            metric_names=("cer", "wer", "mer"),
        ),
        EvaluationView(
            name="caseless",
            candidate_types=frozenset({ArtifactType.RAW_TEXT}),
            metric_names=("cer", "wer", "mer"),
            normalization_profile="caseless",
        ),
    )
    spec = RunSpec(
        corpus=corpus,
        pipelines=tuple(_pipeline(label) for label in _ENGINES),
        evaluation=EvaluationSpec(views=views),
        adapter_kwargs={
            f"precomputed:{label}": {"source_label": label} for label in _ENGINES
        },
        run_id="bnl",
    )
    registry = ModuleRegistry()
    register_default_modules(registry)
    return run_orchestrator(
        spec, registry=registry, code_version=resolve_code_version()
    )


def test_bnl_real_metrics_are_plausible(tmp_path: Path) -> None:
    result = build_bnl_run_result(tmp_path)
    assert {p.pipeline for p in result.pipelines} == set(_ENGINES)
    assert {p.view for p in result.pipelines} == {"text", "caseless"}
    for pipeline in result.pipelines:
        scores = {s.metric: s.value for s in pipeline.aggregate}
        assert set(scores) == {"cer", "wer", "mer"}
        # OCR historique réel (y compris moteur en mauvaise langue) : non nul, borné
        assert scores["cer"] is not None and 0.0 < scores["cer"] < 0.95
    # détail par-document peuplé : N docs × 4 moteurs × 2 vues
    assert len(result.documents) == len(_DOC_IDS) * len(_ENGINES) * 2


def test_bnl_cross_engine_significance_is_live(tmp_path: Path) -> None:
    # n≈30 ≥ _MIN_SUPPORT=6 → le test omnibus CALCULE un p (≠ démo n=3 → tout None).
    result = build_bnl_run_result(tmp_path)
    sig = [s for s in result.cross_engine if s.metric.endswith("significance_p")]
    assert sig, "significativité inter-moteurs attendue dans cross_engine"
    assert any(s.value is not None for s in sig), (
        "n≈30 ≥ plancher 6 → au moins un p-value calculé (pas uniquement None)"
    )


def test_bnl_report_is_octet_stable(tmp_path: Path) -> None:
    result = build_bnl_run_result(tmp_path)
    renderer = default_report_renderer()
    assert renderer.render(result, title="XerOCR — BNL") == renderer.render(
        result, title="XerOCR — BNL"
    )
