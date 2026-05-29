from __future__ import annotations

import pytest

from xerocr.domain import ArtifactType, DocumentRef, GroundTruthRef
from xerocr.domain.errors import CorpusSpecError


def test_path_traversal_rejected():
    with pytest.raises(CorpusSpecError):
        DocumentRef(id="../etc/passwd")


def test_absolute_path_rejected():
    with pytest.raises(CorpusSpecError):
        DocumentRef(id="/etc/passwd")


def test_hierarchical_id_ok():
    assert DocumentRef(id="volA/folio_001").id == "volA/folio_001"


def test_unique_gt_types():
    with pytest.raises(CorpusSpecError):
        DocumentRef(
            id="d",
            ground_truths=(
                GroundTruthRef(type=ArtifactType.RAW_TEXT, uri="a"),
                GroundTruthRef(type=ArtifactType.RAW_TEXT, uri="b"),
            ),
        )


def test_gt_for_and_available():
    d = DocumentRef(
        id="d",
        ground_truths=(GroundTruthRef(type=ArtifactType.RAW_TEXT, uri="a"),),
    )
    gt = d.gt_for(ArtifactType.RAW_TEXT)
    assert gt is not None and gt.uri == "a"
    assert d.gt_for(ArtifactType.ALTO_XML) is None
    assert d.available_gt_types == (ArtifactType.RAW_TEXT,)
