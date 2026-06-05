"""Matérialisation Gallica → ``CorpusSpec`` (images IIIF + OCR étiqueté, sans réseau).

Couvre en particulier le **mapping page→OCR corrigé** (vue ``i`` ↔ ``f{i}``) : la
régression historique ``selected_indices[i]+1`` aurait décalé l'OCR d'une page.
"""

from __future__ import annotations

from pathlib import Path

from xerocr.adapters.corpus.iiif import IIIFImage
from xerocr.app.corpus_import import import_gallica_corpus
from xerocr.domain.artifacts import ArtifactType


class _FakeIIIF:
    def __init__(self, urls: tuple[str, ...]) -> None:
        self._urls = urls
        self.seen_manifest: str | None = None

    def fetch_images(self, manifest_url: str) -> tuple[IIIFImage, ...]:
        self.seen_manifest = manifest_url
        return tuple(
            IIIFImage(image_url=u, label=f"p{i}") for i, u in enumerate(self._urls, 1)
        )


def test_ocr_mapped_by_vue_in_url_not_position(tmp_path: Path) -> None:
    # Canvas 1 (f1) sans image → sauté par le parseur ; restent f2 et f5.
    # Le mapping doit lire la vue dans l'URL (/f{n}/), pas la position dans la liste
    # (sinon décalage : on récupérerait f1/f2 au lieu de f2/f5).
    fake = _FakeIIIF(
        (
            "https://gallica.bnf.fr/iiif/ark:/12148/x/f2/full/full/0/native.jpg",
            "https://gallica.bnf.fr/iiif/ark:/12148/x/f5/full/full/0/native.jpg",
        )
    )
    requested: list[int] = []

    def ocr(vue: int) -> str:
        requested.append(vue)
        return f"ocr vue {vue}"

    spec = import_gallica_corpus(
        "12148/x",
        tmp_path,
        image_importer=fake,  # type: ignore[arg-type]
        download=_writer(),  # type: ignore[arg-type]
        fetch_ocr=ocr,
    )
    assert [d.id for d in spec.documents] == ["f0002", "f0005"]
    assert requested == [2, 5]  # vues lues dans l'URL — pas 1, 2
    assert Path(spec.documents[0].ground_truths[0].uri).read_text() == "ocr vue 2"


def _writer() -> object:
    def _download(
        url: str, dest: Path, *, headers: dict[str, str] | None = None
    ) -> None:
        dest.write_bytes(b"img")

    return _download


def test_images_plus_labeled_ocr_with_correct_mapping(tmp_path: Path) -> None:
    fake = _FakeIIIF(("http://g/1.jpg", "http://g/2.jpg"))
    spec = import_gallica_corpus(
        "ark:/12148/btv1bTEST",
        tmp_path,
        image_importer=fake,  # type: ignore[arg-type]
        download=_writer(),  # type: ignore[arg-type]
        fetch_ocr=lambda page: f"ocr p{page}",
    )
    assert [d.id for d in spec.documents] == ["f0001", "f0002"]
    # OCR Gallica = référence étiquetée REFERENCE_TEXT (≠ vérité-terrain manuelle)
    assert spec.documents[0].ground_truths[0].type == ArtifactType.REFERENCE_TEXT
    # mapping : doc en position i (1-based) ↔ texteBrut f{i} (pas de décalage)
    assert Path(spec.documents[0].ground_truths[0].uri).read_text() == "ocr p1"
    assert Path(spec.documents[1].ground_truths[0].uri).read_text() == "ocr p2"
    assert spec.documents[0].ground_truths[0].uri.endswith("f0001.gallica_ocr.txt")
    # le manifeste interrogé est bien le manifeste IIIF Gallica (préfixe /iiif/)
    assert fake.seen_manifest == (
        "https://gallica.bnf.fr/iiif/ark:/12148/btv1bTEST/manifest.json"
    )
    assert spec.name == "gallica-btv1bTEST"
    assert spec.metadata["source"] == "gallica"
    assert spec.metadata["ark"] == "12148/btv1bTEST"
    assert spec.metadata["gt_source"] == "gallica_ocr"


def test_include_ocr_false_skips_text(tmp_path: Path) -> None:
    fake = _FakeIIIF(("http://g/1.jpg",))
    calls: list[int] = []
    spec = import_gallica_corpus(
        "12148/x",
        tmp_path,
        include_ocr=False,
        image_importer=fake,  # type: ignore[arg-type]
        download=_writer(),  # type: ignore[arg-type]
        fetch_ocr=lambda page: calls.append(page) or "x",  # type: ignore[func-returns-value]
    )
    assert calls == []  # jamais appelé quand include_ocr=False
    assert spec.documents[0].ground_truths == ()
    assert "gt_source" not in spec.metadata


def test_blank_ocr_page_is_image_only(tmp_path: Path) -> None:
    fake = _FakeIIIF(("http://g/1.jpg", "http://g/2.jpg"))
    spec = import_gallica_corpus(
        "12148/x",
        tmp_path,
        image_importer=fake,  # type: ignore[arg-type]
        download=_writer(),  # type: ignore[arg-type]
        fetch_ocr=lambda page: "présent" if page == 1 else "",
    )
    assert len(spec.documents[0].ground_truths) == 1
    assert spec.documents[1].ground_truths == ()
    assert spec.metadata["gt_source"] == "gallica_ocr"  # au moins une vue OCR
