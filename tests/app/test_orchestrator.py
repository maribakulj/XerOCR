"""Orchestrateur : câblage de bout en bout (registre → executor → runner)."""

from __future__ import annotations

from pathlib import Path

import pytest

from xerocr.app import run
from xerocr.app.modules.registry import ModuleRegistry, register_default_modules
from xerocr.app.orchestrator import OrchestrationError
from xerocr.domain.artifacts import ArtifactType
from xerocr.domain.corpus import CorpusSpec
from xerocr.domain.documents import DocumentRef, GroundTruthRef
from xerocr.domain.evaluation import EvaluationSpec, EvaluationView
from xerocr.domain.pipeline import PipelineSpec, PipelineStep
from xerocr.domain.run_spec import RunSpec

TEXT_VIEW = EvaluationView(
    name="text",
    candidate_types=frozenset({ArtifactType.RAW_TEXT}),
    metric_names=("cer",),
)


def _pipeline(name: str, label: str) -> PipelineSpec:
    step = PipelineStep(
        id="ocr",
        kind="ocr",
        adapter_name=f"precomputed:{label}",
        input_types=(ArtifactType.IMAGE,),
        output_types=(ArtifactType.RAW_TEXT,),
    )
    return PipelineSpec(
        name=name, initial_inputs=(ArtifactType.IMAGE,), steps=(step,)
    )


def _registry() -> ModuleRegistry:
    registry = ModuleRegistry()
    register_default_modules(registry)
    return registry


def _spec(corpus: CorpusSpec) -> RunSpec:
    return RunSpec(
        corpus=corpus,
        pipelines=(_pipeline("eng", "eng"),),
        evaluation=EvaluationSpec(views=(TEXT_VIEW,)),
        adapter_kwargs={"precomputed:eng": {"source_label": "eng"}},
    )


def test_run_end_to_end(tmp_path: Path) -> None:
    (tmp_path / "doc1.eng.txt").write_text("abxd", encoding="utf-8")
    (tmp_path / "doc1.gt.txt").write_text("abcd", encoding="utf-8")
    document = DocumentRef(
        id="doc1",
        image_uri=str(tmp_path / "doc1.png"),
        ground_truths=(
            GroundTruthRef(
                type=ArtifactType.RAW_TEXT, uri=str(tmp_path / "doc1.gt.txt")
            ),
        ),
    )
    result = run(
        _spec(CorpusSpec(name="c", documents=(document,))),
        registry=_registry(),
        code_version="1.0",
    )
    aggregate = result.pipelines[0].aggregate[0]
    assert aggregate.metric == "cer"
    assert aggregate.value == pytest.approx(0.25)  # 1 substitution / 4
    assert result.manifest.corpus_name == "c"
    assert result.manifest.n_documents == 1
    assert result.manifest.run_id.startswith("run-")
    assert result.manifest.adapter_kwargs == {
        "precomputed:eng": {"source_label": "eng"}
    }


def test_missing_image_uri_raises(tmp_path: Path) -> None:
    corpus = CorpusSpec(name="c", documents=(DocumentRef(id="doc1"),))
    with pytest.raises(OrchestrationError):
        run(_spec(corpus), registry=_registry(), code_version="1.0")
