from __future__ import annotations

import pickle

import pytest
from pydantic import BaseModel

from xerocr.domain import Deadline
from xerocr.domain.errors import XerOCRError


def test_infinite():
    d = Deadline.infinite()
    assert d.is_infinite
    assert d.remaining_seconds() is None
    assert not d.is_expired()


def test_in_seconds_positive():
    d = Deadline.in_seconds(10)
    remaining = d.remaining_seconds()
    assert remaining is not None and 0 < remaining <= 10
    assert not d.is_expired()


def test_in_seconds_rejects_nonpositive():
    with pytest.raises(XerOCRError):
        Deadline.in_seconds(0)


def test_expired():
    d = Deadline.at_monotonic(0.0)
    assert d.is_expired()
    assert d.remaining_seconds() == 0.0


def test_immutable():
    d = Deadline.infinite()
    with pytest.raises(AttributeError):
        d._expires_at_monotonic = 1.0  # type: ignore[misc]


def test_roundtrip_dict_infinite():
    assert Deadline.from_dict(Deadline.infinite().to_dict()).is_infinite


def test_roundtrip_dict_finite():
    d = Deadline.from_dict(Deadline.in_seconds(30).to_dict())
    remaining = d.remaining_seconds()
    assert remaining is not None and 0 < remaining <= 30


def test_pickle():
    d = pickle.loads(pickle.dumps(Deadline.in_seconds(30)))
    remaining = d.remaining_seconds()
    assert remaining is not None and 0 < remaining <= 30


def test_pydantic_field():
    class M(BaseModel):
        dl: Deadline

    m = M(dl=Deadline.infinite())
    assert m.model_dump()["dl"] == {"remaining_seconds": None}
    m2 = M.model_validate({"dl": {"remaining_seconds": None}})
    assert m2.dl.is_infinite
