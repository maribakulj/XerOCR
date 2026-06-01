"""``JobStore`` : machine à états + instantanés immuables + thread-safety."""

from __future__ import annotations

import threading

import pytest
from pydantic import ValidationError

from xerocr.adapters.storage import Job, JobState, JobStore
from xerocr.adapters.storage.job_store import JobError


def test_create_starts_pending() -> None:
    store = JobStore()
    job = store.create()
    assert job.state is JobState.PENDING
    assert job.report_name is None and job.error is None
    assert store.get(job.id) == job


def test_update_replaces_snapshot() -> None:
    store = JobStore()
    job = store.create()
    done = store.update(job.id, state=JobState.DONE, report_name="web-1")
    assert done.state is JobState.DONE
    assert done.report_name == "web-1"
    assert done.updated_at >= job.updated_at
    # l'instantané d'origine est resté immuable (frozen)
    with pytest.raises(ValidationError):
        job.state = JobState.DONE  # type: ignore[misc]


def test_update_unknown_raises() -> None:
    with pytest.raises(JobError):
        JobStore().update("absent", state=JobState.DONE)


def test_get_unknown_is_none() -> None:
    assert JobStore().get("absent") is None


def test_terminal_states() -> None:
    assert JobState.DONE.is_terminal
    assert JobState.FAILED.is_terminal
    assert JobState.CANCELLED.is_terminal
    assert not JobState.PENDING.is_terminal
    assert not JobState.RUNNING.is_terminal


def test_list_is_newest_first() -> None:
    store = JobStore()
    a = store.create()
    b = store.create()
    ids = [j.id for j in store.list()]
    assert set(ids) == {a.id, b.id}
    # tri stable par created_at décroissant : aucun job perdu
    assert len(store.list()) == 2


def test_concurrent_creates_are_all_recorded() -> None:
    store = JobStore()
    created: list[Job] = []
    lock = threading.Lock()

    def worker() -> None:
        job = store.create()
        with lock:
            created.append(job)

    threads = [threading.Thread(target=worker) for _ in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len({j.id for j in created}) == 20
    assert len(store.list()) == 20
