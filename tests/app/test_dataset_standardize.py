"""Standardiseur de corpus → layout dataset canonique (IIIF statique + GT + carte).

Fixture synthétique (pas de dépendance au ZIP fourni) : un mini-corpus de 2 pages
PAGE + 2 JPEG générés via Pillow, qu'on standardise et dont on vérifie le layout,
``corpus.json``, ``info.json``, la GT et le déterminisme.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cinoc.app.dataset_standardize import (
    DatasetStandardizeError,
    StandardizeConfig,
    standardize_corpus,
)

_PAGE_TMPL = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<PcGts xmlns="http://schema.primaresearch.org/PAGE/gts/pagecontent/2019-07-15">\n'
    '  <Page imageFilename="{img}" imageWidth="2000" imageHeight="3200">\n'
    '    <TextRegion id="r1">\n'
    '      <Coords points="0,0 2000,0 2000,3200 0,3200"/>\n'
    '      <TextLine id="l1"><Coords points="0,0 2000,0 2000,40 0,40"/>'
    "<TextEquiv><Unicode>{line1}</Unicode></TextEquiv></TextLine>\n"
    '      <TextLine id="l2"><Coords points="0,40 2000,40 2000,80 0,80"/>'
    "<TextEquiv><Unicode>second line</Unicode></TextEquiv></TextLine>\n"
    "    </TextRegion>\n"
    "  </Page>\n"
    "</PcGts>\n"
)


def _make_jpg(path: Path, size: tuple[int, int] = (2000, 3200)) -> None:
    from PIL import Image

    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, (200, 180, 160)).save(path, format="JPEG")


def _raw_corpus(root: Path) -> Path:
    """Fabrique ``root/{page,jpg}`` avec 2 pages (dont un nom à espace) + un METS."""
    raw = root / "raw"
    (raw / "page").mkdir(parents=True)
    for stem, line1 in (("page 1", "Hello ſ world"), ("page 2", "zweite Seite")):
        (raw / "page" / f"{stem}.xml").write_text(
            _PAGE_TMPL.format(img=f"{stem}.jpg", line1=line1), encoding="utf-8"
        )
        _make_jpg(raw / "jpg" / f"{stem}.jpg")
    # METS.xml doit être ignoré (pas une page).
    (raw / "page" / "METS.xml").write_text("<mets/>", encoding="utf-8")
    return raw


def _config(
    base_url: str = "https://hf.example/datasets/x/resolve/main",
) -> StandardizeConfig:
    return StandardizeConfig(
        name="Test Corpus",
        stratum="de/17e/kurrent",
        language="de",
        transcription_license="cc-by-nc-sa-4.0",
        image_rights="Public Domain Mark",
        attribution="Tester",
        base_url=base_url,
    )


def test_layout_and_corpus_json(tmp_path: Path) -> None:
    raw = _raw_corpus(tmp_path)
    out = standardize_corpus(raw, tmp_path / "out", _config())

    corpus = json.loads((out / "corpus.json").read_text(encoding="utf-8"))
    assert corpus["name"] == "Test Corpus"
    assert corpus["license"] == {
        "transcription": "cc-by-nc-sa-4.0",
        "images": "Public Domain Mark",
    }
    ids = [d["id"] for d in corpus["documents"]]
    assert ids == ["page_1", "page_2"]  # espace → underscore, ordre trié
    doc = corpus["documents"][0]
    assert doc["stratum"] == "de/17e/kurrent"
    assert doc["image"] == "iiif/page_1/full/1600,/0/default.jpg"
    assert doc["thumbnail"] == "iiif/page_1/full/400,/0/default.jpg"
    # Tous les chemins référencés existent réellement.
    for rel in (doc["image"], doc["thumbnail"], doc["ground_truth"], doc["page_xml"]):
        assert (out / rel).is_file()
    assert (out / "iiif/page_1/full/max/0/default.jpg").is_file()


def test_ground_truth_text_preserves_lines_and_long_s(tmp_path: Path) -> None:
    raw = _raw_corpus(tmp_path)
    out = standardize_corpus(raw, tmp_path / "out", _config())
    gt = (out / "ground_truth/page_1.gt.txt").read_text(encoding="utf-8")
    assert gt == "Hello ſ world\nsecond line"  # lignes jointes, ſ préservé


def test_iiif_info_json_level0(tmp_path: Path) -> None:
    raw = _raw_corpus(tmp_path)
    out = standardize_corpus(raw, tmp_path / "out", _config())
    info = json.loads((out / "iiif/page_1/info.json").read_text(encoding="utf-8"))
    assert info["profile"] == "level0"
    assert info["type"] == "ImageService3"
    assert info["width"] == 2000 and info["height"] == 3200
    assert info["id"].endswith("/iiif/page_1")
    # Tailles = largeurs exactes demandées (jamais agrandi), hauteurs proportionnelles.
    assert info["sizes"] == [
        {"width": 400, "height": 640},
        {"width": 1600, "height": 2560},
    ]


def test_deterministic(tmp_path: Path) -> None:
    raw = _raw_corpus(tmp_path)
    a = standardize_corpus(raw, tmp_path / "a", _config())
    b = standardize_corpus(raw, tmp_path / "b", _config())
    for rel in ("corpus.json", "README.md", "iiif/page_1/info.json",
                "ground_truth/page_1.gt.txt"):
        assert (a / rel).read_bytes() == (b / rel).read_bytes()


def test_card_has_license_frontmatter(tmp_path: Path) -> None:
    raw = _raw_corpus(tmp_path)
    out = standardize_corpus(raw, tmp_path / "out", _config())
    card = (out / "README.md").read_text(encoding="utf-8")
    assert card.startswith("---\nlicense: cc-by-nc-sa-4.0\n")
    assert "Public Domain Mark" in card


def test_missing_subdirs_raise(tmp_path: Path) -> None:
    (tmp_path / "raw").mkdir()
    with pytest.raises(DatasetStandardizeError, match="layout brut"):
        standardize_corpus(tmp_path / "raw", tmp_path / "out", _config())


def test_page_without_image_raises(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    (raw / "page").mkdir(parents=True)
    (raw / "jpg").mkdir()
    (raw / "page" / "orphan.xml").write_text(
        _PAGE_TMPL.format(img="orphan.jpg", line1="x"), encoding="utf-8"
    )
    with pytest.raises(DatasetStandardizeError, match="image absente"):
        standardize_corpus(raw, tmp_path / "out", _config())
