from __future__ import annotations

import pytest
from pydantic import ValidationError

from xerocr.domain import Artifact, ArtifactType, compute_content_hash
from xerocr.domain.errors import ArtifactValidationError


def test_layout_is_first_class():
    assert ArtifactType.LAYOUT.value == "layout"


def test_reference_text_value():
    # Référence OCR (≠ GT manuelle) ; valeur sérialisée stable (round-trip JSON).
    assert ArtifactType.REFERENCE_TEXT.value == "reference_text"
    assert ArtifactType("reference_text") is ArtifactType.REFERENCE_TEXT


def test_short_aliases_via_missing():
    assert ArtifactType("text") is ArtifactType.RAW_TEXT
    assert ArtifactType("alto") is ArtifactType.ALTO_XML
    assert ArtifactType("page") is ArtifactType.PAGE_XML


def test_no_python_alias_members():
    assert not hasattr(ArtifactType, "TEXT")
    assert not hasattr(ArtifactType, "ALTO")
    assert not hasattr(ArtifactType, "PAGE")


def test_compute_content_hash_known_vector():
    assert compute_content_hash(b"abc") == (
        "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )


def test_artifact_frozen():
    a = Artifact(id="a", document_id="d", type=ArtifactType.RAW_TEXT)
    with pytest.raises(ValidationError):
        a.id = "b"


def test_region_id():
    a = Artifact(id="a", document_id="d", type=ArtifactType.LAYOUT)
    assert a.region_id is None
    b = Artifact(id="a", document_id="d", type=ArtifactType.LAYOUT, region_id="r1")
    assert b.region_id == "r1"


def test_bad_id_rejected():
    with pytest.raises(ArtifactValidationError):
        Artifact(id="bad id!", document_id="d", type=ArtifactType.RAW_TEXT)


def test_content_hash_rejects_non_hex():
    with pytest.raises(ArtifactValidationError):
        Artifact(
            id="a", document_id="d", type=ArtifactType.RAW_TEXT,
            content_hash="z" * 64,
        )


def test_content_hash_normalized_lower():
    h = "AB" * 32
    a = Artifact(
        id="a", document_id="d", type=ArtifactType.RAW_TEXT, content_hash=h,
    )
    assert a.content_hash == h.lower()
