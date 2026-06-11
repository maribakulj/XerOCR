"""Adapter vignettes : image → data-URI redimensionné, dégradé gracieux."""

from __future__ import annotations

from pathlib import Path

import pytest

from xerocr.adapters.images import thumbnail_data_uri

PIL = pytest.importorskip("PIL")  # extra [images] ; sans Pillow → adapter rend None


def _png(path: Path, size: tuple[int, int]) -> Path:
    from PIL import Image

    Image.new("RGB", size, (210, 200, 180)).save(path)
    return path


def test_resizes_to_jpeg_data_uri(tmp_path: Path) -> None:
    uri = thumbnail_data_uri(_png(tmp_path / "x.png", (800, 600)), max_px=120)
    assert uri is not None
    assert uri.startswith("data:image/jpeg;base64,")


def test_never_upscales(tmp_path: Path) -> None:
    from PIL import Image

    uri = thumbnail_data_uri(_png(tmp_path / "small.png", (40, 30)), max_px=280)
    assert uri is not None
    import base64
    import io

    raw = base64.b64decode(uri.split(",", 1)[1])
    with Image.open(io.BytesIO(raw)) as img:
        assert img.size == (40, 30)  # jamais agrandi


def test_missing_file_returns_none(tmp_path: Path) -> None:
    assert thumbnail_data_uri(tmp_path / "nope.png") is None


def test_unreadable_returns_none(tmp_path: Path) -> None:
    bad = tmp_path / "bad.png"
    bad.write_text("pas une image", encoding="utf-8")
    assert thumbnail_data_uri(bad) is None  # illisible → None, pas d'exception
