"""Matérialisation HuggingFace → ``CorpusSpec`` scorable (stream injecté, sans lib)."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from xerocr.adapters.corpus.huggingface import HFPage
from xerocr.app.corpus_import import CorpusImportError, import_hf_corpus
from xerocr.domain.artifacts import ArtifactType


def _stream(pages: list[HFPage]):
    def _s(
        dataset_id: str, *, split: str = "train", limit: int | None = None
    ) -> Iterator[HFPage]:
        yield from pages[:limit] if limit is not None else pages

    return _s


def test_builds_scorable_corpus_with_real_gt(tmp_path: Path) -> None:
    pages = [
        HFPage(image_bytes=b"PNG1", image_ext=".png", gt_text="au nom de Dieu"),
        HFPage(image_bytes=b"JPG2", image_ext=".jpg", gt_text="   "),  # GT blanche
    ]
    spec = import_hf_corpus(
        "org/corpus-xerocr", tmp_path, stream=_stream(pages)
    )
    assert spec.name == "hf-org-corpus-xerocr"
    assert spec.metadata == {
        "source": "huggingface",
        "dataset_id": "org/corpus-xerocr",
        "split": "train",
    }
    assert [d.id for d in spec.documents] == ["page_0001", "page_0002"]

    # page 1 : image écrite + vraie GT RAW_TEXT (dataset curé = vérité-terrain)
    img = Path(spec.documents[0].image_uri)
    assert img.read_bytes() == b"PNG1" and img.name == "page_0001.png"
    gts = spec.documents[0].ground_truths
    assert len(gts) == 1 and gts[0].type == ArtifactType.RAW_TEXT
    assert Path(gts[0].uri).read_text(encoding="utf-8") == "au nom de Dieu"

    # page 2 : GT blanche → image seule
    assert spec.documents[1].ground_truths == ()


def test_empty_stream_raises(tmp_path: Path) -> None:
    with pytest.raises(CorpusImportError, match="aucune page"):
        import_hf_corpus("org/empty", tmp_path, stream=_stream([]))
