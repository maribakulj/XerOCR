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
from xerocr.evaluation.result import RunResult

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


# ── isolation des workspaces + provenance (corrections d'audit) ─────────────
def _ocr_llm_pipeline(name: str, ocr_label: str) -> PipelineSpec:
    return PipelineSpec(
        name=name,
        initial_inputs=(ArtifactType.IMAGE,),
        steps=(
            PipelineStep(
                id="ocr",
                kind="ocr",
                adapter_name=f"precomputed:{ocr_label}",
                input_types=(ArtifactType.IMAGE,),
                output_types=(ArtifactType.RAW_TEXT,),
            ),
            PipelineStep(
                id="llm",
                kind="post_correction",
                adapter_name="openai:gpt",  # PARTAGÉ par les deux pipelines
                input_types=(ArtifactType.RAW_TEXT,),
                output_types=(ArtifactType.CORRECTED_TEXT,),
                inputs_from={ArtifactType.RAW_TEXT: "ocr"},
            ),
        ),
    )


def _shared_writer_spec(tmp_path: Path) -> RunSpec:
    # OCR pré-calculé distinct par pipeline ; GT = la sortie attendue de A.
    (tmp_path / "d.gt.txt").write_text("alpha", encoding="utf-8")
    (tmp_path / "d.engA.txt").write_text("alpha", encoding="utf-8")
    (tmp_path / "d.engB.txt").write_text("beta", encoding="utf-8")
    document = DocumentRef(
        id="d",
        image_uri=str(tmp_path / "d.png"),
        ground_truths=(
            GroundTruthRef(type=ArtifactType.RAW_TEXT, uri=str(tmp_path / "d.gt.txt")),
        ),
    )
    view = EvaluationView(
        name="corrected",
        candidate_types=frozenset({ArtifactType.CORRECTED_TEXT}),
        metric_names=("cer",),
    )
    return RunSpec(
        corpus=CorpusSpec(name="c", documents=(document,)),
        pipelines=(_ocr_llm_pipeline("A", "engA"), _ocr_llm_pipeline("B", "engB")),
        evaluation=EvaluationSpec(views=(view,)),
        adapter_kwargs={
            "precomputed:engA": {"source_label": "engA"},
            "precomputed:engB": {"source_label": "engB"},
            "openai:gpt": {"label": "gpt"},
        },
        run_id="t",
    )


def _cer(result: RunResult, pipeline: str) -> float | None:
    (value,) = (
        score.value
        for pr in result.pipelines
        if pr.pipeline == pipeline
        for score in pr.aggregate
        if score.metric == "cer"
    )
    return value


def test_pipelines_sharing_a_writer_do_not_contaminate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # LLM mocké : renvoie le texte OCR reçu (dernier segment du prompt) → la
    # sortie corrigée diffère par pipeline puisque l'OCR amont diffère.
    monkeypatch.setattr(
        "xerocr.adapters.llm.openai._invoke_openai",
        lambda *, model, prompt, deadline: prompt.rsplit("\n\n", 1)[-1],
    )
    result = run(
        _shared_writer_spec(tmp_path), registry=_registry(), code_version="9.9"
    )
    # A corrige "alpha" == GT → CER 0 ; B corrige "beta" != GT → CER > 0. Sans
    # isolation par pipeline, B écraserait le fichier de A → CER de A faussement > 0.
    assert _cer(result, "A") == 0.0
    assert (_cer(result, "B") or 0.0) > 0.0


def test_manifest_captures_module_versions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "xerocr.adapters.llm.openai._invoke_openai",
        lambda *, model, prompt, deadline: "x",
    )
    result = run(
        _shared_writer_spec(tmp_path), registry=_registry(), code_version="9.9"
    )
    # R-2 : la version déclarée de chaque module exécuté entre dans l'empreinte.
    assert result.manifest.module_versions == {
        "openai:gpt": "1.0",
        "precomputed:engA": "1.0",
        "precomputed:engB": "1.0",
    }
