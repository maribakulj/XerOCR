from __future__ import annotations

import pytest

from xerocr.domain import CorpusSpec, DocumentRef
from xerocr.domain.errors import CorpusSpecError


def test_unique_doc_ids():
    with pytest.raises(CorpusSpecError):
        CorpusSpec(name="c", documents=(DocumentRef(id="d"), DocumentRef(id="d")))


def test_len_and_lookup():
    c = CorpusSpec(name="c", documents=(DocumentRef(id="a"), DocumentRef(id="b")))
    assert len(c) == 2
    found = c.doc_by_id("b")
    assert found is not None and found.id == "b"
    assert c.doc_by_id("z") is None
