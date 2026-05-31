"""Pipeline multi-étapes OCR → LLM : produit du ``CORRECTED_TEXT`` non vide."""

from __future__ import annotations

from pathlib import Path

import pytest

from xerocr.adapters.llm.openai import OpenAIAdapter
from xerocr.adapters.ocr.precomputed import PrecomputedTextAdapter
from xerocr.domain.artifacts import Artifact, ArtifactType
from xerocr.domain.pipeline import PipelineSpec, PipelineStep
from xerocr.pipeline.executor import PipelineExecutor


def test_ocr_then_llm_produces_corrected_text(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "doc1.eng.txt").write_text("Hello wrld", encoding="utf-8")
    monkeypatch.setattr(
        "xerocr.adapters.llm.openai._invoke_openai", lambda **_: "Hello world"
    )
    ocr = PipelineStep(
        id="ocr",
        kind="ocr",
        adapter_name="precomputed:eng",
        input_types=(ArtifactType.IMAGE,),
        output_types=(ArtifactType.RAW_TEXT,),
    )
    llm = PipelineStep(
        id="llm",
        kind="post_correction",
        adapter_name="openai:gpt",
        input_types=(ArtifactType.RAW_TEXT,),
        output_types=(ArtifactType.CORRECTED_TEXT,),
        inputs_from={ArtifactType.RAW_TEXT: "ocr"},
    )
    spec = PipelineSpec(
        name="ocr_llm", initial_inputs=(ArtifactType.IMAGE,), steps=(ocr, llm)
    )
    modules = {
        "precomputed:eng": PrecomputedTextAdapter(source_label="eng"),
        "openai:gpt": OpenAIAdapter(label="gpt"),
    }
    image = Artifact(
        id="doc1:init:image",
        document_id="doc1",
        type=ArtifactType.IMAGE,
        uri=str(tmp_path / "doc1.png"),
    )

    pool = PipelineExecutor("1.0").execute_document(
        spec,
        modules,
        {ArtifactType.IMAGE: image},
        document_id="doc1",
        workspace_uri=str(tmp_path),
    )

    assert ArtifactType.CORRECTED_TEXT in pool
    corrected = pool[ArtifactType.CORRECTED_TEXT]
    assert corrected.uri is not None
    assert Path(corrected.uri).read_text(encoding="utf-8") == "Hello world"
