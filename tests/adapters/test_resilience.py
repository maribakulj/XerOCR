"""Résilience réseau : cap de concurrence par fournisseur + retry borné 429/5xx.

Tout est déterministe : ``sleep``/``jitter`` injectés, exceptions factices avec
``status_code``/``headers``. Le câblage live de Mistral est ``# pragma: no cover``
(réseau + clé) ; ici on couvre le mécanisme générique qu'il consomme.
"""

from __future__ import annotations

import threading
import time

import pytest

from cinoc.adapters._resilience import (
    call_resilient,
    http_is_retryable,
    http_retry_after,
    network_slot,
)


class _FakeHTTPError(Exception):
    """Imite une erreur SDK httpx : porte ``status_code`` (+ ``headers`` option.)."""

    def __init__(self, status_code: int, headers: dict[str, str] | None = None) -> None:
        super().__init__(f"HTTP {status_code}")
        self.status_code = status_code
        if headers is not None:
            self.headers = headers


# --- prédicats HTTP -------------------------------------------------------


def test_is_retryable_on_429_and_5xx() -> None:
    assert http_is_retryable(_FakeHTTPError(429))
    assert http_is_retryable(_FakeHTTPError(503))


def test_not_retryable_on_4xx_or_no_status() -> None:
    assert not http_is_retryable(_FakeHTTPError(400))
    assert not http_is_retryable(ValueError("réseau coupé"))  # pas de status_code


def test_retry_after_reads_header() -> None:
    assert http_retry_after(_FakeHTTPError(429, {"retry-after": "7"})) == 7.0


def test_retry_after_absent_is_none() -> None:
    assert http_retry_after(_FakeHTTPError(429)) is None
    assert http_retry_after(_FakeHTTPError(429, {"x": "y"})) is None


def test_retry_after_is_capped() -> None:
    # Un Retry-After absurde est borné (anti-blocage).
    assert http_retry_after(_FakeHTTPError(429, {"retry-after": "9999"})) == 30.0


# --- call_resilient -------------------------------------------------------


def test_returns_first_success_without_retry() -> None:
    calls = []

    def once() -> str:
        calls.append(1)
        return "ok"

    result = call_resilient("p-ok", once, sleep=lambda d: None)
    assert result == "ok"
    assert len(calls) == 1


def test_retries_then_succeeds() -> None:
    attempts = {"n": 0}
    slept: list[float] = []

    def flaky() -> str:
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise _FakeHTTPError(429)
        return "done"

    result = call_resilient(
        "p-flaky", flaky, sleep=slept.append, jitter=lambda: 0.0
    )
    assert result == "done"
    assert attempts["n"] == 3
    assert len(slept) == 2  # deux attentes entre trois tentatives


def test_honours_retry_after() -> None:
    slept: list[float] = []

    def always_429() -> str:
        raise _FakeHTTPError(429, {"retry-after": "5"})

    with pytest.raises(_FakeHTTPError):
        call_resilient("p-ra", always_429, attempts=2, sleep=slept.append)
    assert slept == [5.0]  # le Retry-After serveur prime sur le backoff calculé


def test_gives_up_after_attempts() -> None:
    attempts = {"n": 0}

    def always_503() -> str:
        attempts["n"] += 1
        raise _FakeHTTPError(503)

    with pytest.raises(_FakeHTTPError):
        call_resilient(
            "p-503", always_503, attempts=4, sleep=lambda d: None, jitter=lambda: 0.0
        )
    assert attempts["n"] == 4  # épuise les tentatives puis relance la dernière


def test_does_not_retry_non_retryable() -> None:
    attempts = {"n": 0}

    def bad_request() -> str:
        attempts["n"] += 1
        raise _FakeHTTPError(400)

    with pytest.raises(_FakeHTTPError):
        call_resilient("p-400", bad_request, sleep=lambda d: None)
    assert attempts["n"] == 1  # 4xx → échec immédiat, pas de retry


# --- cap de concurrence (network_slot) ------------------------------------


def test_slot_caps_concurrency_per_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CINOC_NETWORK_CONCURRENCY", "2")
    provider = "test-cap-2"  # nom frais : plafond figé à 2 à la création
    active = 0
    peak = 0
    lock = threading.Lock()

    def worker() -> None:
        nonlocal active, peak
        with network_slot(provider):
            with lock:
                active += 1
                peak = max(peak, active)
            time.sleep(0.02)
            with lock:
                active -= 1

    threads = [threading.Thread(target=worker) for _ in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert peak <= 2  # jamais plus de 2 appels simultanés malgré 6 threads


def test_invalid_env_falls_back_to_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CINOC_NETWORK_CONCURRENCY", "pas-un-entier")
    # Ne lève pas : nom frais → plafond défaut (3), au moins 1 détenteur possible.
    with network_slot("test-bad-env"):
        assert True
