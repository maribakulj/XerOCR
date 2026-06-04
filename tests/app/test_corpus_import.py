"""Matérialisation IIIF → ``CorpusSpec`` (importer + download injectés, sans réseau)."""

from __future__ import annotations

from pathlib import Path

import pytest

from xerocr.adapters.corpus.iiif import IIIFImage
from xerocr.app.corpus_import import CorpusImportError, import_iiif_corpus


class _FakeImporter:
    def __init__(self, images: tuple[IIIFImage, ...]) -> None:
        self._images = images

    def fetch_images(self, manifest_url: str) -> tuple[IIIFImage, ...]:
        return self._images


def _writer(record: dict[str, Path]):
    def _download(
        url: str, dest: Path, *, headers: dict[str, str] | None = None
    ) -> None:
        dest.write_bytes(b"fake-image-bytes")
        record[url] = dest

    return _download


def test_materializes_corpus_spec(tmp_path: Path) -> None:
    images = (
        IIIFImage("https://ex.org/a.jpg", "A"),
        IIIFImage("https://ex.org/iiif/b/full/max/0/default.jpg", "B"),
    )
    written: dict[str, Path] = {}
    spec = import_iiif_corpus(
        "https://ex.org/m.json",
        tmp_path,
        name="iiif-test",
        importer=_FakeImporter(images),  # type: ignore[arg-type]
        download=_writer(written),
    )
    assert spec.name == "iiif-test"
    assert [d.id for d in spec.documents] == ["page_0001", "page_0002"]
    # extension dérivée de l'URL (.jpg direct ; service → défaut .jpg)
    assert spec.documents[0].image_uri.endswith("page_0001.jpg")
    assert spec.documents[1].image_uri.endswith("page_0002.jpg")
    # images seules → aucune vérité-terrain
    assert all(d.ground_truths == () for d in spec.documents)
    assert spec.metadata == {"source": "iiif", "manifest_url": "https://ex.org/m.json"}
    # fichiers réellement écrits sous dest
    for doc in spec.documents:
        path = Path(doc.image_uri)
        assert path.exists()
        assert str(tmp_path) in doc.image_uri


def test_limit_truncates_pages(tmp_path: Path) -> None:
    images = tuple(IIIFImage(f"https://ex.org/{i}.png", str(i)) for i in range(5))
    spec = import_iiif_corpus(
        "https://ex.org/m.json",
        tmp_path,
        name="c",
        limit=2,
        importer=_FakeImporter(images),  # type: ignore[arg-type]
        download=_writer({}),
    )
    assert len(spec.documents) == 2
    assert spec.documents[0].image_uri.endswith("page_0001.png")


def test_empty_manifest_raises(tmp_path: Path) -> None:
    with pytest.raises(CorpusImportError):
        import_iiif_corpus(
            "https://ex.org/m.json",
            tmp_path,
            name="c",
            importer=_FakeImporter(()),  # type: ignore[arg-type]
            download=_writer({}),
        )
