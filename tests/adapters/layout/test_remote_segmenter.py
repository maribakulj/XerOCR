"""``RemoteSegmenter`` : conversion détections HF→LAYOUT, contrat ``Module``, garde.

Le détecteur HTTP est **injecté** : la conversion réponse HF → ``CanonicalLayout``
et le contrat ``Module`` se prouvent **sans réseau** (CI). Le vrai appel ``httpx``
(``_remote_detect``) reste un test ``live`` (non couvert ici).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cinoc.adapters.layout._base import DetectedRegion, LayoutDetection
from cinoc.adapters.layout.remote import RemoteSegmenter, parse_hf_detections
from cinoc.domain.artifacts import Artifact, ArtifactType
from cinoc.domain.errors import AdapterStepError
from cinoc.domain.layout import CanonicalLayout
from cinoc.pipeline.run_control import RunControl
from cinoc.pipeline.types import RunContext


def _scene(tmp_path: Path) -> tuple[Artifact, RunContext]:
    image = tmp_path / "doc1.png"
    image.write_bytes(b"\x89PNG stub")
    art = Artifact(
        id="doc1:initial:image", document_id="doc1",
        type=ArtifactType.IMAGE, uri=str(image),
    )
    ctx = RunContext(
        document_id="doc1", code_version="1.0", pipeline_name="seg",
        workspace_uri=str(tmp_path),
    )
    return art, ctx


def _fixed(detection: LayoutDetection):
    return lambda _path: detection


def _hf_box(label: str, score: float, x0: int, y0: int, x1: int, y1: int) -> dict:
    return {
        "label": label,
        "score": score,
        "box": {"xmin": x0, "ymin": y0, "xmax": x1, "ymax": y1},
    }


# --- parse_hf_detections : tolérance + correction géométrie ---------------------


def test_parse_hf_detections_maps_boxes() -> None:
    payload = [
        _hf_box("title", 0.95, 40, 30, 480, 100),
        _hf_box("paragraph", 0.90, 40, 130, 250, 480),
    ]
    detection = parse_hf_detections(payload, page_width=600, page_height=800)
    assert detection.page_width == 600 and detection.page_height == 800
    assert tuple(r.label for r in detection.regions) == ("title", "paragraph")
    first = detection.regions[0]
    assert (first.x, first.y, first.width, first.height) == (40, 30, 440, 70)
    assert first.score == 0.95


def test_parse_hf_detections_skips_malformed_items() -> None:
    payload = [
        _hf_box("ok", 0.9, 0, 0, 10, 10),
        "not-a-dict",
        {"label": "no-box", "score": 0.9},
        {"label": "bad-box", "box": {"xmin": "x"}},
        {"label": "partial", "box": {"xmin": 1, "ymin": 2}},  # xmax/ymax manquants
    ]
    detection = parse_hf_detections(payload, page_width=100, page_height=100)
    assert tuple(r.label for r in detection.regions) == ("ok",)


def test_parse_hf_detections_rejects_non_list() -> None:
    with pytest.raises(AdapterStepError, match="liste de détections"):
        parse_hf_detections({"oops": 1}, page_width=10, page_height=10)


# --- contrat Module ------------------------------------------------------------


def test_execute_converts_detections_to_layout(tmp_path: Path) -> None:
    detection = LayoutDetection(
        page_width=600, page_height=800,
        regions=(
            DetectedRegion("title", 40, 30, 440, 70, 0.95),
            DetectedRegion("paragraph", 40, 130, 210, 350, 0.90),
        ),
    )
    seg = RemoteSegmenter(
        endpoint="https://example.org/seg", detector=_fixed(detection)
    )
    art, ctx = _scene(tmp_path)
    out = seg.execute({ArtifactType.IMAGE: art}, {}, ctx, RunControl())
    layout = CanonicalLayout.model_validate_json(
        Path(out.artifacts[ArtifactType.LAYOUT].uri).read_bytes()  # type: ignore[arg-type]
    )
    page = layout.pages[0]
    assert page.width == 600 and page.height == 800
    assert tuple(r.region_type for r in page.regions) == ("title", "paragraph")
    assert all(r.lines == () for r in page.regions)


def test_min_score_filters_low_confidence(tmp_path: Path) -> None:
    detection = LayoutDetection(
        page_width=100, page_height=120,
        regions=(
            DetectedRegion("title", 0, 0, 10, 10, 0.9),
            DetectedRegion("noise", 0, 50, 10, 10, 0.2),
        ),
    )
    seg = RemoteSegmenter(
        endpoint="https://example.org/seg", min_score=0.5, detector=_fixed(detection)
    )
    art, ctx = _scene(tmp_path)
    out = seg.execute({ArtifactType.IMAGE: art}, {}, ctx, RunControl())
    layout = CanonicalLayout.model_validate_json(
        Path(out.artifacts[ArtifactType.LAYOUT].uri).read_bytes()  # type: ignore[arg-type]
    )
    assert tuple(r.region_type for r in layout.pages[0].regions) == ("title",)


def test_module_contract_types() -> None:
    seg = RemoteSegmenter(endpoint="https://example.org/seg")
    assert seg.name == "remote_segmenter"
    assert seg.input_types == frozenset({ArtifactType.IMAGE})
    assert seg.output_types == frozenset({ArtifactType.LAYOUT})


def test_endpoint_required() -> None:
    with pytest.raises(AdapterStepError, match="endpoint"):
        RemoteSegmenter(endpoint="")


def test_invalid_min_score_rejected() -> None:
    with pytest.raises(AdapterStepError, match="min_score"):
        RemoteSegmenter(endpoint="https://example.org/seg", min_score=1.5)


def test_execute_requires_image(tmp_path: Path) -> None:
    _, ctx = _scene(tmp_path)
    seg = RemoteSegmenter(
        endpoint="https://example.org/seg",
        detector=_fixed(LayoutDetection(page_width=0, page_height=0, regions=())),
    )
    with pytest.raises(AdapterStepError, match="IMAGE"):
        seg.execute({}, {}, ctx, RunControl())
