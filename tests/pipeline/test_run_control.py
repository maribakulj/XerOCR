"""``RunControl`` — annulation coopérative."""

from __future__ import annotations

import threading

import pytest

from xerocr.domain.errors import RunCancelledError
from xerocr.pipeline.run_control import RunControl


def test_not_cancelled_by_default() -> None:
    c = RunControl()
    assert c.is_cancelled() is False
    assert c.cancel_triggered is False
    c.raise_if_cancelled()  # ne lève pas


def test_trigger_then_raises() -> None:
    c = RunControl()
    c.trigger_cancel()
    assert c.is_cancelled() is True
    assert c.cancel_triggered is True
    with pytest.raises(RunCancelledError):
        c.raise_if_cancelled()


def test_trigger_is_idempotent() -> None:
    c = RunControl()
    c.trigger_cancel()
    c.trigger_cancel()
    assert c.is_cancelled() is True


def test_shared_event_drives_state() -> None:
    event = threading.Event()
    c = RunControl(event)
    assert c.is_cancelled() is False
    event.set()
    assert c.is_cancelled() is True
