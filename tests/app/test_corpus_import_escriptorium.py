"""Matérialisation eScriptorium → ``CorpusSpec`` scorable (importer + I/O injectés)."""

from __future__ import annotations

from pathlib import Path

import pytest

from xerocr.adapters.corpus.escriptorium import EScriptoriumPage
from xerocr.app.corpus_import import CorpusImportError, import_escriptorium_corpus
from xerocr.domain.artifacts import ArtifactType


class _FakeImporter:
    def __init__(self, pages: tuple[EScriptoriumPage, ...]) -> None:
        self._pages = pages

    def fetch_pages(self, doc_pk: int) -> tuple[EScriptoriumPage, ...]:
        return self._pages


def _writer() -> object:
    def _download(url: str, dest: Path) -> None:
        dest.write_bytes(b"fake-image")

    return _download


def test_builds_scorable_corpus_with_gt(tmp_path: Path) -> None:
    pages = (
        EScriptoriumPage(
            pk=42, image_url="http://e.org/a.png", gt_text="hello\nworld", title="f.1"
        ),
        EScriptoriumPage(
            pk=43, image_url="http://e.org/b.jpg", gt_text="   ", title="f.2"
        ),
    )
    spec = import_escriptorium_corpus(
        "http://e.org/",
        "tok",
        5,
        tmp_path,
        importer=_FakeImporter(pages),  # type: ignore[arg-type]
        download=_writer(),  # type: ignore[arg-type]
    )
    assert spec.name == "escriptorium-5"
    assert [d.id for d in spec.documents] == ["part_00042", "part_00043"]

    # page 1 : GT écrite, niveau RAW_TEXT pointant vers le .gt.txt
    gts = spec.documents[0].ground_truths
    assert len(gts) == 1 and gts[0].type == ArtifactType.RAW_TEXT
    assert Path(gts[0].uri).read_text(encoding="utf-8") == "hello\nworld"
    assert gts[0].uri.endswith("part_00042.gt.txt")

    # page 2 : GT blanche → image seule (pas de niveau GT fabriqué)
    assert spec.documents[1].ground_truths == ()

    assert spec.metadata == {
        "source": "escriptorium",
        "base_url": "http://e.org",
        "doc_pk": "5",
        "layer": "manual",
    }


def test_page_without_image_is_skipped(tmp_path: Path) -> None:
    pages = (
        EScriptoriumPage(pk=1, image_url="", gt_text="x", title="t"),
        EScriptoriumPage(pk=2, image_url="http://e.org/b.png", gt_text="y", title="t"),
    )
    spec = import_escriptorium_corpus(
        "http://e.org",
        "tok",
        9,
        tmp_path,
        importer=_FakeImporter(pages),  # type: ignore[arg-type]
        download=_writer(),  # type: ignore[arg-type]
    )
    assert [d.id for d in spec.documents] == ["part_00002"]


def test_no_usable_page_raises(tmp_path: Path) -> None:
    pages = (EScriptoriumPage(pk=1, image_url="", gt_text="x", title="t"),)
    with pytest.raises(CorpusImportError):
        import_escriptorium_corpus(
            "http://e.org",
            "tok",
            9,
            tmp_path,
            importer=_FakeImporter(pages),  # type: ignore[arg-type]
            download=_writer(),  # type: ignore[arg-type]
        )
