"""Transcription locale : corpus depuis un dossier d'images + écriture des ALTO."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from cinoc.app.transcription import (
    TranscriptionError,
    corpus_from_images,
    write_alto_files,
)
from cinoc.domain.artifacts import Artifact, ArtifactType

_DOC_ID_RE = re.compile(r"^[A-Za-z0-9_.\-/]+$")


def test_corpus_one_document_per_image(tmp_path: Path) -> None:
    (tmp_path / "page1.png").write_bytes(b"x")
    (tmp_path / "page2.jpg").write_bytes(b"x")
    (tmp_path / "notes.txt").write_text("ignore", encoding="utf-8")  # non-image
    corpus = corpus_from_images(tmp_path)
    assert corpus.name == tmp_path.name
    assert [d.id for d in corpus.documents] == ["page1", "page2"]
    assert all(d.image_uri and d.ground_truths == () for d in corpus.documents)


def test_corpus_sanitizes_and_dedupes_ids(tmp_path: Path) -> None:
    (tmp_path / "café.png").write_bytes(b"x")  # accent → caractère sûr
    (tmp_path / "cafe.png").write_bytes(b"x")
    ids = [d.id for d in corpus_from_images(tmp_path).documents]
    assert len(set(ids)) == len(ids)  # uniques (déduplication)
    assert all(_DOC_ID_RE.match(i) for i in ids)  # ids valides


def test_corpus_empty_dir_raises(tmp_path: Path) -> None:
    with pytest.raises(TranscriptionError):
        corpus_from_images(tmp_path)


def test_corpus_missing_dir_raises(tmp_path: Path) -> None:
    with pytest.raises(TranscriptionError):
        corpus_from_images(tmp_path / "absent")


def test_write_alto_files_copies_per_document(tmp_path: Path) -> None:
    src = tmp_path / "doc1.alto.xml"
    src.write_bytes(b"<alto/>")
    outputs = {
        "hybrid": {
            "doc1": {
                ArtifactType.ALTO_XML: Artifact(
                    id="doc1:assemble:alto_xml",
                    document_id="doc1",
                    type=ArtifactType.ALTO_XML,
                    uri=str(src),
                ),
            },
            "doc2": {  # pas d'ALTO → ignoré
                ArtifactType.RAW_TEXT: Artifact(
                    id="doc2:ocr:raw_text",
                    document_id="doc2",
                    type=ArtifactType.RAW_TEXT,
                    uri=str(src),
                ),
            },
        }
    }
    out = tmp_path / "out"
    written = write_alto_files(out, outputs)
    assert written == [out / "doc1.alto.xml"]
    assert (out / "doc1.alto.xml").read_bytes() == b"<alto/>"
