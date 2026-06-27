from __future__ import annotations

import pytest

from cinoc.domain.errors import (
    AdapterStepError,
    ArtifactValidationError,
    CinocError,
    CorpusSpecError,
    DeadlineExceeded,
    ProjectionError,
    RunCancelledError,
)


def test_hierarchy():
    assert issubclass(DeadlineExceeded, AdapterStepError)
    assert issubclass(AdapterStepError, CinocError)
    for exc in (
        CorpusSpecError,
        ProjectionError,
        ArtifactValidationError,
        RunCancelledError,
    ):
        assert issubclass(exc, CinocError)


def test_catch_root():
    with pytest.raises(CinocError):
        raise DeadlineExceeded("x")


def test_run_cancelled_distinct_from_deadline():
    assert not issubclass(RunCancelledError, DeadlineExceeded)
