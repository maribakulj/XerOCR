"""Importeur de layout dataset canonique → ``CorpusSpec`` (variante réf-IIIF).

Teste l'importeur en isolation (layout écrit à la main) + un **round-trip** réel
``standardize_corpus`` → ``import_curated_corpus`` (les deux moitiés s'emboîtent).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cinoc.app.corpus_import import (
    CorpusImportError,
    import_curated_corpus,
    import_curated_hf_corpus,
)
from cinoc.app.dataset_standardize import StandardizeConfig, standardize_corpus
from cinoc.domain.artifacts import ArtifactType

_IMG_REL = "iiif/d1/full/1600,/0/default.jpg"


def _layout(root: Path, *, gt_rel: str = "ground_truth/d1.gt.txt",
            image_rel: str = _IMG_REL) -> Path:
    """Écrit un layout canonique minimal (1 document) à la main."""
    (root / "ground_truth").mkdir(parents=True, exist_ok=True)
    (root / "ground_truth" / "d1.gt.txt").write_text("hello ſ", encoding="utf-8")
    medium = root / "iiif/d1/full/1600,/0"
    medium.mkdir(parents=True, exist_ok=True)
    (medium / "default.jpg").write_bytes(b"jpeg-bytes")
    manifest = {
        "name": "Layout test",
        "license": {"transcription": "cc-by-nc-sa-4.0", "images": "Public Domain Mark"},
        "documents": [{
            "id": "d1", "image": image_rel,
            "thumbnail": "iiif/d1/full/400,/0/default.jpg",
            "ground_truth": gt_rel, "stratum": "de/17e/kurrent",
        }],
    }
    (root / "corpus.json").write_text(json.dumps(manifest), encoding="utf-8")
    return root


def test_import_with_base_url_yields_iiif_reference(tmp_path: Path) -> None:
    root = _layout(tmp_path / "ds")
    spec = import_curated_corpus(
        root, base_url="https://hf.example/datasets/x/resolve/abc123", revision="abc123"
    )
    assert len(spec) == 1
    doc = spec.documents[0]
    assert doc.id == "d1"
    # image = URL IIIF distante (référence, pas d'octets).
    assert doc.image_uri == f"https://hf.example/datasets/x/resolve/abc123/{_IMG_REL}"
    assert doc.metadata["stratum"] == "de/17e/kurrent"
    # GT = vraie GT RAW_TEXT, résolvable et lisible.
    gt = doc.gt_for(ArtifactType.RAW_TEXT)
    assert gt is not None and Path(gt.uri).read_text(encoding="utf-8") == "hello ſ"
    # Repro + provenance dans la métadonnée corpus.
    assert spec.metadata["source"] == "curated"
    assert spec.metadata["revision"] == "abc123"
    assert spec.metadata["license_transcription"] == "cc-by-nc-sa-4.0"


def test_import_without_base_url_yields_local_path(tmp_path: Path) -> None:
    root = _layout(tmp_path / "ds")
    spec = import_curated_corpus(root)
    doc = spec.documents[0]
    assert doc.image_uri == str(root / _IMG_REL)
    assert Path(doc.image_uri).is_file()
    assert "revision" not in spec.metadata


def test_missing_manifest_raises(tmp_path: Path) -> None:
    with pytest.raises(CorpusImportError, match="corpus.json"):
        import_curated_corpus(tmp_path)


def test_path_traversal_in_manifest_rejected(tmp_path: Path) -> None:
    root = _layout(tmp_path / "ds", gt_rel="../../etc/secret")
    with pytest.raises(CorpusImportError, match="non sûr"):
        import_curated_corpus(root)


def test_hf_import_pins_iiif_to_revision(tmp_path: Path) -> None:
    # fetch injecté (pas de réseau) → renvoie un layout local ; l'URL IIIF des
    # images est épinglée à la révision sur huggingface.co.
    layout = _layout(tmp_path / "ds")
    seen: dict[str, object] = {}

    def _fetch(repo_id: str, dest: Path, revision: str | None) -> Path:
        seen["repo_id"] = repo_id
        seen["revision"] = revision
        return layout

    spec = import_curated_hf_corpus(
        "Ma-Ri-Ba-Ku/Cinoc-Dresden",
        tmp_path / "dl",
        revision="abc123",
        name="Dresden",
        fetch=_fetch,
    )
    assert seen == {"repo_id": "Ma-Ri-Ba-Ku/Cinoc-Dresden", "revision": "abc123"}
    doc = spec.documents[0]
    assert doc.image_uri == (
        "https://huggingface.co/datasets/Ma-Ri-Ba-Ku/Cinoc-Dresden/resolve/abc123/"
        f"{_IMG_REL}"
    )
    assert spec.name == "Dresden"
    assert spec.metadata["revision"] == "abc123"
    assert spec.metadata["source"] == "curated"
    # GT rapatriée localement et lisible.
    gt = doc.gt_for(ArtifactType.RAW_TEXT)
    assert gt is not None and Path(gt.uri).read_text(encoding="utf-8") == "hello ſ"


def test_hf_import_defaults_to_main_without_revision(tmp_path: Path) -> None:
    layout = _layout(tmp_path / "ds")
    spec = import_curated_hf_corpus(
        "org/ds", tmp_path / "dl", fetch=lambda _r, _d, _rev: layout
    )
    doc = spec.documents[0]
    assert "/resolve/main/" in doc.image_uri
    assert "revision" not in spec.metadata  # non épinglé → pas de fausse provenance


def test_round_trip_standardize_then_import(tmp_path: Path) -> None:
    # Corpus brut minimal (1 page PAGE + 1 JPEG) → standardise → importe.
    from PIL import Image

    raw = tmp_path / "raw"
    (raw / "page").mkdir(parents=True)
    (raw / "jpg").mkdir()
    page_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<PcGts xmlns="http://schema.primaresearch.org/PAGE/gts/pagecontent/2019-07-15">\n'
        '  <Page imageFilename="f1.jpg" imageWidth="1200" imageHeight="1600">\n'
        '    <TextRegion id="r1"><Coords points="0,0 1200,0 1200,1600 0,1600"/>\n'
        '      <TextLine id="l1"><Coords points="0,0 1200,0 1200,40 0,40"/>'
        "<TextEquiv><Unicode>Sontagk den 25.</Unicode></TextEquiv></TextLine>\n"
        "    </TextRegion>\n  </Page>\n</PcGts>\n"
    )
    (raw / "page" / "f1.xml").write_text(page_xml, encoding="utf-8")
    Image.new("RGB", (1200, 1600), (210, 200, 190)).save(raw / "jpg" / "f1.jpg")

    layout = standardize_corpus(raw, tmp_path / "ds", StandardizeConfig(
        name="RT", stratum="de/17e/kurrent", language="de",
        transcription_license="cc-by-nc-sa-4.0", image_rights="Public Domain Mark",
        attribution="Tester",
    ))
    spec = import_curated_corpus(layout, base_url="https://hf.example/x/resolve/main")
    doc = spec.documents[0]
    assert doc.id == "f1"
    assert doc.image_uri.startswith("https://hf.example/x/resolve/main/iiif/f1/")
    gt = doc.gt_for(ArtifactType.RAW_TEXT)
    assert gt is not None
    assert Path(gt.uri).read_text(encoding="utf-8") == "Sontagk den 25."
