"""Pipeline de segmentation **déclarative** de bout en bout.

Prouve que les trois étages — segmentation → reconnaissance **par région
(fanout)** → assemblage ALTO — s'orchestrent par une **`PipelineSpec` unique**,
modules résolus via la **factory du registre** (pas d'appel direct), puis que la
sortie `ALTO_XML` se recharge comme layout et se mesure (`region_cer`).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from xerocr.app.modules.registry import ModuleRegistry, register_default_modules
from xerocr.domain.artifacts import Artifact, ArtifactType
from xerocr.domain.layout import CanonicalLayout, LayoutPage, Line, Region
from xerocr.domain.pipeline import PipelineSpec, PipelineStep
from xerocr.evaluation.context import DocContext
from xerocr.evaluation.metrics.layout import region_cer
from xerocr.evaluation.representations import load_representation
from xerocr.pipeline.executor import PipelineExecutor

CODE_VERSION = "test-1.0"


def _segmentation_pipeline() -> PipelineSpec:
    return PipelineSpec(
        name="segmentation",
        initial_inputs=(ArtifactType.IMAGE,),
        steps=(
            PipelineStep(
                id="segment",
                kind="segmentation",
                adapter_name="precomputed_layout",
                input_types=(ArtifactType.IMAGE,),
                output_types=(ArtifactType.LAYOUT,),
            ),
            PipelineStep(
                id="recognize",
                kind="recognition",
                adapter_name="precomputed_region:eng",
                input_types=(ArtifactType.LAYOUT, ArtifactType.IMAGE),
                output_types=(ArtifactType.LAYOUT,),
                inputs_from={ArtifactType.LAYOUT: "segment"},
                fanout=True,
            ),
            PipelineStep(
                id="assemble",
                kind="assembly",
                adapter_name="alto_assembler",
                input_types=(ArtifactType.LAYOUT,),
                output_types=(ArtifactType.ALTO_XML,),
                inputs_from={ArtifactType.LAYOUT: "recognize"},
            ),
        ),
    )


def _modules(registry: ModuleRegistry) -> dict[str, object]:
    return {
        "precomputed_layout": registry.build("precomputed_layout", {}),
        "precomputed_region:eng": registry.build(
            "precomputed_region:eng", {"source_label": "eng"}
        ),
        "alto_assembler": registry.build("alto_assembler", {}),
    }


def _scene(tmp_path: Path, regions: dict[str, str]) -> Artifact:
    image = tmp_path / "doc1.png"
    image.write_bytes(b"\x89PNG stub")
    seg = CanonicalLayout(
        pages=(
            LayoutPage(
                regions=(
                    Region(id="r1", region_type="text"),
                    Region(id="r2", region_type="text"),
                ),
                reading_order=("r1", "r2"),
            ),
        )
    )
    (tmp_path / "doc1.layout.json").write_bytes(seg.model_dump_json().encode("utf-8"))
    (tmp_path / "doc1.eng.regions.json").write_text(
        json.dumps(regions), encoding="utf-8"
    )
    return Artifact(
        id="doc1:init:image",
        document_id="doc1",
        type=ArtifactType.IMAGE,
        uri=str(image),
    )


def _gt_layout() -> CanonicalLayout:
    return CanonicalLayout(
        pages=(
            LayoutPage(
                regions=(
                    Region(id="r1", lines=(Line(text="hello world"),)),
                    Region(id="r2", lines=(Line(text="second block"),)),
                ),
            ),
        )
    )


def _run(tmp_path: Path, regions: dict[str, str]) -> dict[ArtifactType, Artifact]:
    image = _scene(tmp_path, regions)
    registry = ModuleRegistry()
    register_default_modules(registry)
    return PipelineExecutor(CODE_VERSION).execute_document(
        _segmentation_pipeline(),
        _modules(registry),  # type: ignore[arg-type]
        {ArtifactType.IMAGE: image},
        document_id="doc1",
        workspace_uri=str(tmp_path),
    )


def test_spec_round_trips_with_fanout_flag() -> None:
    spec = _segmentation_pipeline()
    assert PipelineSpec.model_validate(spec.model_dump()) == spec
    assert spec.step_by_id("recognize").fanout is True  # type: ignore[union-attr]


def test_declarative_pipeline_runs_three_stages(tmp_path: Path) -> None:
    pool = _run(tmp_path, {"r1": "hello world", "r2": "second blocX"})
    # L'étage fan-out a produit un LAYOUT rempli, estampillé par l'exécuteur.
    filled = pool.artifacts[ArtifactType.LAYOUT]
    assert filled.produced_by_step == "recognize"
    assert filled.provenance is not None
    assert filled.provenance.code_version == CODE_VERSION
    # L'assemblage a produit l'ALTO_XML.
    alto = pool.artifacts[ArtifactType.ALTO_XML]
    assert alto.produced_by_step == "assemble"
    assert alto.uri is not None
    assert Path(alto.uri).read_bytes().lstrip().startswith(b"<")


def test_pipeline_output_reloads_and_scores(tmp_path: Path) -> None:
    pool = _run(tmp_path, {"r1": "hello world", "r2": "second blocX"})
    alto_uri = pool.artifacts[ArtifactType.ALTO_XML].uri
    assert alto_uri is not None
    hyp = load_representation(alto_uri, ArtifactType.LAYOUT)
    score = region_cer.fn(
        DocContext(document_id="doc1", reference=_gt_layout(), hypothesis=hyp)
    )
    assert score is not None
    assert score.value == pytest.approx(1 / 23)  # 1 faute / (11 + 12) chars


def test_partial_failure_survives_declarative_run(tmp_path: Path) -> None:
    # r2 absente des textes → région non reconnue, page non abattue.
    pool = _run(tmp_path, {"r1": "hello world"})
    filled = CanonicalLayout.model_validate_json(
        Path(pool.artifacts[ArtifactType.LAYOUT].uri).read_bytes()  # type: ignore[arg-type]
    )
    page = filled.pages[0]
    assert page.regions[0].lines[0].text == "hello world"
    assert page.regions[1].lines == ()
