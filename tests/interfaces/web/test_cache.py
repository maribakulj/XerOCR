"""``TTLCache`` (F1) : mémoïsation à expiration, horloge injectée (sans dormir)."""

from __future__ import annotations

import pytest

from xerocr.interfaces.web._cache import TTLCache


class _Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def test_hit_within_ttl_computes_once() -> None:
    clock = _Clock()
    cache: TTLCache[str, int] = TTLCache(10.0, clock=clock)
    calls = {"n": 0}

    def compute() -> int:
        calls["n"] += 1
        return 42

    assert cache.get_or_compute("k", compute) == 42
    clock.now = 9.0  # toujours dans la fenêtre
    assert cache.get_or_compute("k", compute) == 42
    assert calls["n"] == 1  # une seule fois (cache chaud)


def test_recomputes_after_expiry() -> None:
    clock = _Clock()
    cache: TTLCache[str, int] = TTLCache(10.0, clock=clock)
    calls = {"n": 0}

    def compute() -> int:
        calls["n"] += 1
        return calls["n"]

    assert cache.get_or_compute("k", compute) == 1
    clock.now = 11.0  # TTL dépassé
    assert cache.get_or_compute("k", compute) == 2
    assert calls["n"] == 2


def test_distinct_keys_are_independent() -> None:
    cache: TTLCache[str, str] = TTLCache(10.0, clock=_Clock())
    assert cache.get_or_compute("a", lambda: "A") == "A"
    assert cache.get_or_compute("b", lambda: "B") == "B"


def test_failure_is_not_cached() -> None:
    clock = _Clock()
    cache: TTLCache[str, int] = TTLCache(10.0, clock=clock)
    calls = {"n": 0}

    def flaky() -> int:
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("réseau indisponible")
        return 7

    with pytest.raises(RuntimeError):
        cache.get_or_compute("k", flaky)
    # l'échec n'a rien figé : le 2ᵉ appel recalcule (et réussit)
    assert cache.get_or_compute("k", flaky) == 7
    assert calls["n"] == 2
