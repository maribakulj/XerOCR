from __future__ import annotations

import pytest

from xerocr.domain.errors import (
    AdapterStepError,
    ArtifactValidationError,
    CorpusSpecError,
    DeadlineExceeded,
    ProjectionError,
    RunCancelledError,
    XerOCRError,
)


def test_hierarchy():
    assert issubclass(DeadlineExceeded, AdapterStepError)
    assert issubclass(AdapterStepError, XerOCRError)
    for exc in (
        CorpusSpecError,
        ProjectionError,
        ArtifactValidationError,
        RunCancelledError,
    ):
        assert issubclass(exc, XerOCRError)


def test_catch_root():
    with pytest.raises(XerOCRError):
        raise DeadlineExceeded("x")


def test_run_cancelled_distinct_from_deadline():
    assert not issubclass(RunCancelledError, DeadlineExceeded)
