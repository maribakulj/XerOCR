"""``SegmentationStore`` : persistance layout + image, relecture, anti-traversal."""

from __future__ import annotations

from pathlib import Path

from xerocr.app.segmentation import SegmentationStore, demo_layout, demo_page_image


def test_save_and_get_layout_roundtrip(tmp_path: Path) -> None:
    store = SegmentationStore(tmp_path)
    layout = demo_layout()
    seg_id = store.save(layout)
    assert store.get_layout(seg_id) == layout


def test_save_persists_image_and_exposes_path(tmp_path: Path) -> None:
    store = SegmentationStore(tmp_path)
    seg_id = store.save(demo_layout(), image_ext=".png", image_bytes=demo_page_image())
    path = store.image_path(seg_id)
    assert path is not None
    assert path.suffix == ".png"
    assert path.read_bytes() == demo_page_image()


def test_image_path_is_none_without_image(tmp_path: Path) -> None:
    store = SegmentationStore(tmp_path)
    seg_id = store.save(demo_layout())
    assert store.image_path(seg_id) is None


def test_get_layout_unknown_id_is_none(tmp_path: Path) -> None:
    assert SegmentationStore(tmp_path).get_layout("does-not-exist") is None


def test_traversal_id_is_rejected(tmp_path: Path) -> None:
    store = SegmentationStore(tmp_path)
    # Un id qui tenterait de sortir de la base est confiné → None (pas d'exception).
    assert store.get_layout("../etc/passwd") is None
    assert store.image_path("../../secret") is None


def test_demo_page_image_is_deterministic_png() -> None:
    first = demo_page_image()
    assert first[:8] == b"\x89PNG\r\n\x1a\n"
    assert first == demo_page_image()
