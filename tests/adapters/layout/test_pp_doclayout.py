"""``PPDocLayoutSegmenter`` (T2.1) : conversion détections→LAYOUT, exécution, SDK.

Le **détecteur est injecté** : la conversion et le contrat ``Module`` se prouvent
sans PaddleX ni poids (CI). Le vrai modèle reste un test ``live`` (non couvert ici).
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from xerocr.adapters.layout.pp_doclayout import (
    DetectedRegion,
    LayoutDetection,
    PPDocLayoutSegmenter,
)
from xerocr.domain.artifacts import Artifact, ArtifactType
from xerocr.domain.errors import AdapterStepError
from xerocr.domain.layout import CanonicalLayout
from xerocr.pipeline.run_control import RunControl
from xerocr.pipeline.types import RunContext


def _detection(*regions: DetectedRegion, w: int = 600, h: int = 800) -> LayoutDetection:
    return LayoutDetection(page_width=w, page_height=h, regions=regions)


def _fixed(detection: LayoutDetection):
    """Détecteur injecté renvoyant une détection figée (ignore le chemin image)."""
    return lambda _path: detection


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


def test_converts_detections_to_layout_regions(tmp_path: Path) -> None:
    detection = _detection(
        DetectedRegion("title", 40, 30, 440, 70, 0.95),
        DetectedRegion("paragraph", 40, 130, 210, 350, 0.90),
    )
    seg = PPDocLayoutSegmenter(detector=_fixed(detection))
    art, ctx = _scene(tmp_path)
    out = seg.execute({ArtifactType.IMAGE: art}, {}, ctx, RunControl())
    layout = CanonicalLayout.model_validate_json(
        Path(out[ArtifactType.LAYOUT].uri).read_bytes()  # type: ignore[arg-type]
    )
    page = layout.pages[0]
    assert page.width == 600 and page.height == 800
    assert tuple(r.region_type for r in page.regions) == ("title", "paragraph")
    box = page.regions[0].geometry.bbox  # type: ignore[union-attr]
    assert (box.x, box.y, box.width, box.height) == (40, 30, 440, 70)
    # segmentation = régions SANS lignes (la reconnaissance les remplit ensuite)
    assert all(r.lines == () for r in page.regions)


def test_min_score_filters_low_confidence(tmp_path: Path) -> None:
    detection = _detection(
        DetectedRegion("title", 0, 0, 10, 10, 0.9),
        DetectedRegion("noise", 0, 50, 10, 10, 0.2),
    )
    seg = PPDocLayoutSegmenter(min_score=0.5, detector=_fixed(detection))
    art, ctx = _scene(tmp_path)
    out = seg.execute({ArtifactType.IMAGE: art}, {}, ctx, RunControl())
    layout = CanonicalLayout.model_validate_json(
        Path(out[ArtifactType.LAYOUT].uri).read_bytes()  # type: ignore[arg-type]
    )
    assert tuple(r.region_type for r in layout.pages[0].regions) == ("title",)


def test_reading_order_is_sorted_top_to_bottom(tmp_path: Path) -> None:
    # détections dans le désordre → ordre de lecture trié (y puis x), pas l'ordre brut
    detection = _detection(
        DetectedRegion("c", 0, 200, 10, 10, 0.9),
        DetectedRegion("a", 0, 10, 10, 10, 0.9),
        DetectedRegion("b", 300, 10, 10, 10, 0.9),
    )
    seg = PPDocLayoutSegmenter(detector=_fixed(detection))
    art, ctx = _scene(tmp_path)
    out = seg.execute({ArtifactType.IMAGE: art}, {}, ctx, RunControl())
    layout = CanonicalLayout.model_validate_json(
        Path(out[ArtifactType.LAYOUT].uri).read_bytes()  # type: ignore[arg-type]
    )
    page = layout.pages[0]
    assert tuple(r.region_type for r in page.regions) == ("a", "b", "c")
    assert page.reading_order == ("r1", "r2", "r3")


def test_execute_produces_hashed_layout_artifact(tmp_path: Path) -> None:
    seg = PPDocLayoutSegmenter(
        detector=_fixed(_detection(DetectedRegion("t", 1, 2, 3, 4, 0.9)))
    )
    art, ctx = _scene(tmp_path)
    out = seg.execute({ArtifactType.IMAGE: art}, {}, ctx, RunControl())
    layout_art = out[ArtifactType.LAYOUT]
    assert layout_art.type is ArtifactType.LAYOUT
    assert layout_art.uri is not None and Path(layout_art.uri).is_file()
    assert layout_art.content_hash is not None and len(layout_art.content_hash) == 64


def test_render_is_deterministic(tmp_path: Path) -> None:
    detection = _detection(
        DetectedRegion("a", 0, 10, 5, 5, 0.9), DetectedRegion("b", 0, 20, 5, 5, 0.9)
    )
    art, ctx = _scene(tmp_path)
    first = PPDocLayoutSegmenter(detector=_fixed(detection)).execute(
        {ArtifactType.IMAGE: art}, {}, ctx, RunControl()
    )
    second = PPDocLayoutSegmenter(detector=_fixed(detection)).execute(
        {ArtifactType.IMAGE: art}, {}, ctx, RunControl()
    )
    assert first[ArtifactType.LAYOUT].content_hash == (
        second[ArtifactType.LAYOUT].content_hash
    )


def test_execute_requires_image(tmp_path: Path) -> None:
    _, ctx = _scene(tmp_path)
    seg = PPDocLayoutSegmenter(detector=_fixed(_detection()))
    with pytest.raises(AdapterStepError, match="IMAGE"):
        seg.execute({}, {}, ctx, RunControl())


def test_execute_requires_workspace(tmp_path: Path) -> None:
    art, _ = _scene(tmp_path)
    ctx = RunContext(document_id="doc1", code_version="1.0", pipeline_name="seg")
    seg = PPDocLayoutSegmenter(detector=_fixed(_detection()))
    with pytest.raises(AdapterStepError, match="workspace"):
        seg.execute({ArtifactType.IMAGE: art}, {}, ctx, RunControl())


def test_invalid_min_score_rejected() -> None:
    with pytest.raises(AdapterStepError, match="min_score"):
        PPDocLayoutSegmenter(min_score=1.5)


@pytest.mark.skipif(
    importlib.util.find_spec("paddlex") is not None,
    reason="PaddleX installé → chemin réel (test live)",
)
def test_missing_sdk_raises_friendly_error(tmp_path: Path) -> None:
    # Sans détecteur injecté ni extra [segment] : message d'install clair, pas de crash.
    art, ctx = _scene(tmp_path)
    seg = PPDocLayoutSegmenter()
    with pytest.raises(AdapterStepError, match=r"\[segment\]"):
        seg.execute({ArtifactType.IMAGE: art}, {}, ctx, RunControl())
