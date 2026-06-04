"""Import HuggingFace en **streaming** (convention XerOCR), loader injecté.

Couvre le chemin réel ``stream_pages`` sans la lib ``datasets`` : un loader
factice renvoie des lignes (image en octets + ``ground_truth``) comme le ferait
``Image(decode=False)``. Le vrai branchement ``datasets`` est un extra,
exercé seulement par un test opt-in (hors sandbox).
"""

from __future__ import annotations

from collections.abc import Iterable

import pytest

from xerocr.adapters.corpus import huggingface as hf
from xerocr.adapters.corpus.huggingface import (
    HuggingFaceConventionError,
    stream_pages,
)


def _row(img: bytes, gt: str, path: str = "x.png") -> dict[str, object]:
    return {"image": {"bytes": img, "path": path}, "ground_truth": gt}


def _loader(rows: list[dict[str, object]]):
    def _load(dataset_id: str, split: str) -> Iterable[object]:
        return iter(rows)

    return _load


def test_streams_conformant_pages() -> None:
    rows = [_row(b"PNG1", "texte 1", "a.png"), _row(b"JPG2", "texte 2", "b.jpeg")]
    pages = list(stream_pages("org/ds", loader=_loader(rows)))
    assert [p.image_bytes for p in pages] == [b"PNG1", b"JPG2"]
    assert [p.image_ext for p in pages] == [".png", ".jpeg"]
    assert [p.gt_text for p in pages] == ["texte 1", "texte 2"]


def test_limit_bounds_pages() -> None:
    rows = [_row(b"x", str(i)) for i in range(10)]
    pages = list(stream_pages("org/ds", limit=3, loader=_loader(rows)))
    assert len(pages) == 3


def test_missing_ground_truth_column_is_convention_error() -> None:
    rows = [{"image": {"bytes": b"x", "path": "a.png"}}]  # pas de ground_truth
    with pytest.raises(HuggingFaceConventionError, match="ground_truth"):
        list(stream_pages("org/ds", loader=_loader(rows)))


def test_image_without_bytes_is_convention_error() -> None:
    rows = [{"image": {"path": "a.png"}, "ground_truth": "g"}]  # pas d'octets
    with pytest.raises(HuggingFaceConventionError, match="octets"):
        list(stream_pages("org/ds", loader=_loader(rows)))


def test_oversized_image_skipped(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(hf, "IMAGE_MAX_BYTES", 4)
    rows = [_row(b"ok", "petit"), _row(b"trop-gros", "grand"), _row(b"ok2", "petit2")]
    pages = list(stream_pages("org/ds", loader=_loader(rows)))
    # l'image > 4 octets est ignorée ; les deux petites passent
    assert [p.gt_text for p in pages] == ["petit", "petit2"]


def test_unknown_extension_defaults_to_jpg() -> None:
    pages = list(stream_pages("org/ds", loader=_loader([_row(b"x", "g", "a.bin")])))
    assert pages[0].image_ext == ".jpg"
