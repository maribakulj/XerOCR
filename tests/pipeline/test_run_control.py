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


def test_handle_fires_on_cancel() -> None:
    c = RunControl()
    calls: list[int] = []
    c.register_cancel_handle(lambda: calls.append(1))
    assert calls == []  # pas encore annulé → pas appelé
    c.trigger_cancel()
    assert calls == [1]


def test_register_after_cancel_fires_immediately() -> None:
    c = RunControl()
    c.trigger_cancel()
    calls: list[int] = []
    c.register_cancel_handle(lambda: calls.append(1))
    assert calls == [1]  # déjà annulé → effet immédiat (pas de course perdue)


def test_handle_fires_once_on_repeated_trigger() -> None:
    c = RunControl()
    calls: list[int] = []
    c.register_cancel_handle(lambda: calls.append(1))
    c.trigger_cancel()
    c.trigger_cancel()  # idempotent : le handle n'est pas rappelé
    assert calls == [1]


def test_all_handles_fire_in_order() -> None:
    c = RunControl()
    order: list[str] = []
    c.register_cancel_handle(lambda: order.append("a"))
    c.register_cancel_handle(lambda: order.append("b"))
    c.trigger_cancel()
    assert order == ["a", "b"]
