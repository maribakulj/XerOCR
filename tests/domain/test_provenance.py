from __future__ import annotations

import time

from xerocr.domain import ProvenanceRecord


def test_is_compatible_ignores_timestamp():
    a = ProvenanceRecord(code_version="1", parameters_hash="h")
    time.sleep(0.001)
    b = ProvenanceRecord(code_version="1", parameters_hash="h")
    assert a.timestamp != b.timestamp
    assert a.is_compatible_with(b)


def test_incompatible_when_params_differ():
    a = ProvenanceRecord(code_version="1", parameters_hash="h")
    c = ProvenanceRecord(code_version="1", parameters_hash="other")
    assert not a.is_compatible_with(c)
