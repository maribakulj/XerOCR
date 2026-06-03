"""Mapper ``alto_to_layout`` + consommateur réel (chargement d'une GT ALTO).

Épaississement T5 : le modèle neutre lit du **vrai ALTO**. Prouve la projection
structurelle (régions/lignes/mots/géométrie/ordre) puis le bout-en-bout
``region_cer`` sur des GT/hyp **sourcées ALTO** via ``load_representation``.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from xerocr.domain.artifacts import Artifact, ArtifactType
from xerocr.domain.corpus import CorpusSpec
from xerocr.domain.documents import DocumentRef, GroundTruthRef
from xerocr.domain.evaluation import EvaluationSpec, EvaluationView
from xerocr.domain.layout import BBox
from xerocr.domain.pipeline import PipelineSpec
from xerocr.domain.run import RunManifest
from xerocr.evaluation.registry import MetricRegistry, register_default_metrics
from xerocr.evaluation.representations import load_representation
from xerocr.evaluation.runner import evaluate_run
from xerocr.formats.alto import (
    AltoBBox,
    AltoComposedBlock,
    AltoDocument,
    AltoIllustration,
    AltoLine,
    AltoPage,
    AltoString,
    AltoTextBlock,
    write_alto,
)
from xerocr.formats.alto.layout_map import alto_to_layout

FIXED = datetime(2026, 1, 1, tzinfo=UTC)


def _line(*words: str) -> AltoLine:
    return AltoLine(strings=tuple(AltoString(content=w) for w in words))


def _block(
    block_id: str | None, *words: str, bbox: AltoBBox | None = None
) -> AltoTextBlock:
    return AltoTextBlock(id=block_id, bbox=bbox, lines=(_line(*words),))


def _doc(*blocks: AltoTextBlock, width: int = 100, height: int = 50) -> AltoDocument:
    return AltoDocument(pages=(AltoPage(width=width, height=height, blocks=blocks),))


def test_maps_regions_lines_words_and_order() -> None:
    doc = _doc(
        _block(
            "b1", "hello", "world",
            bbox=AltoBBox(hpos=1, vpos=2, width=3, height=4),
        ),
        _block("b2", "second", "block"),
    )
    layout = alto_to_layout(doc)
    page = layout.pages[0]
    assert (page.width, page.height) == (100, 50)
    assert page.reading_order == ("b1", "b2")
    r1, r2 = page.regions
    assert r1.id == "b1" and r1.region_type == "text"
    assert r1.lines[0].text == "hello world"
    assert tuple(w.text for w in r1.lines[0].words) == ("hello", "world")
    assert r1.geometry is not None
    assert r1.geometry.bbox == BBox(x=1, y=2, width=3, height=4)
    assert r2.lines[0].text == "second block"


def test_synthesizes_missing_region_ids() -> None:
    layout = alto_to_layout(_doc(_block(None, "a"), _block(None, "b")))
    assert tuple(r.id for r in layout.pages[0].regions) == ("region_0", "region_1")


def test_composed_block_becomes_nested_regions() -> None:
    composed = AltoComposedBlock(id="c1", blocks=(_block("b1", "x"),))
    layout = alto_to_layout(_doc(composed))  # type: ignore[arg-type]
    outer = layout.pages[0].regions[0]
    assert outer.id == "c1" and outer.region_type == "composed"
    assert outer.regions[0].id == "b1"
    assert outer.regions[0].lines[0].text == "x"


def test_non_text_block_has_no_lines() -> None:
    layout = alto_to_layout(_doc(AltoIllustration(id="i1")))  # type: ignore[arg-type]
    region = layout.pages[0].regions[0]
    assert region.region_type == "illustration"
    assert region.lines == ()


def test_load_representation_reads_alto_as_layout(tmp_path: Path) -> None:
    path = tmp_path / "gt.alto.xml"
    path.write_bytes(write_alto(_doc(_block("b1", "hello", "world"))))
    loaded = load_representation(str(path), ArtifactType.LAYOUT)
    region = loaded.pages[0].regions[0]  # type: ignore[attr-defined]
    assert region.lines[0].text == "hello world"


def test_load_representation_still_reads_json_layout(tmp_path: Path) -> None:
    layout = alto_to_layout(_doc(_block("b1", "hi")))
    path = tmp_path / "gt.layout.json"
    path.write_bytes(layout.model_dump_json().encode("utf-8"))
    loaded = load_representation(str(path), ArtifactType.LAYOUT)
    assert loaded == layout


def _registry() -> MetricRegistry:
    registry = MetricRegistry()
    register_default_metrics(registry)
    return registry


def test_region_cer_end_to_end_over_alto_gt(tmp_path: Path) -> None:
    gt_doc = _doc(_block("b1", "hello", "world"), _block("b2", "second", "block"))
    hyp_doc = _doc(_block("b1", "hello", "world"), _block("b2", "second", "blocX"))
    gt = tmp_path / "doc1.gt.alto.xml"
    gt.write_bytes(write_alto(gt_doc))
    hyp = tmp_path / "doc1.hyp.alto.xml"
    hyp.write_bytes(write_alto(hyp_doc))
    doc = DocumentRef(
        id="doc1",
        ground_truths=(GroundTruthRef(type=ArtifactType.LAYOUT, uri=str(gt)),),
    )
    outputs = {
        "seg": {
            "doc1": {
                ArtifactType.LAYOUT: Artifact(
                    id="doc1:assemble:layout",
                    document_id="doc1",
                    type=ArtifactType.LAYOUT,
                    uri=str(hyp),
                )
            }
        }
    }
    result = evaluate_run(
        corpus=CorpusSpec(name="c", documents=(doc,)),
        evaluation=EvaluationSpec(
            views=(
                EvaluationView(
                    name="structure",
                    candidate_types=frozenset({ArtifactType.LAYOUT}),
                    metric_names=("region_cer",),
                ),
            )
        ),
        pipeline_outputs=outputs,
        registry=_registry(),
        manifest=RunManifest(
            run_id="r",
            corpus_name="c",
            n_documents=1,
            pipeline_specs=(
                PipelineSpec(name="seg", initial_inputs=(ArtifactType.IMAGE,)),
            ),
            code_version="1.0",
            started_at=FIXED,
            completed_at=FIXED,
        ),
    )
    # b1 exact (0/11) ; b2 1 substitution (1/12) → micro page = 1/23.
    aggregate = result.pipelines[0].aggregate[0]
    assert aggregate.metric == "region_cer"
    assert aggregate.value == pytest.approx(1 / 23)
    assert aggregate.support == 1
