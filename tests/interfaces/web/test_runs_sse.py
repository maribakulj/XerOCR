"""Flux SSE du lanceur (TU2.e) : événements ordonnés + reprise ``Last-Event-ID``.

On lance un run et on **attend qu'il soit terminé** avant d'ouvrir le flux : le
journal est alors complet, donc la diffusion est **déterministe** (rejeu intégral
puis fermeture) — aucune course de timing.
"""

from __future__ import annotations

import time
from pathlib import Path

from fastapi.testclient import TestClient

from xerocr.interfaces.web.app import create_app
from xerocr.interfaces.web.security.csrf import CSRF_HEADER

_CSRF = {CSRF_HEADER: "1"}


def _client(tmp_path: Path) -> TestClient:
    return TestClient(create_app(reports_dir=tmp_path, rate_limit=1000))


def _launch_and_finish(client: TestClient) -> str:
    job_id = client.post("/api/runs", headers=_CSRF).json()["job_id"]
    deadline = time.time() + 30.0
    while time.time() < deadline:
        if client.get(f"/api/runs/{job_id}").json()["state"] in {
            "done", "failed", "cancelled"
        }:
            return job_id
        time.sleep(0.02)
    raise AssertionError("job non terminé")


def _parse_sse(text: str) -> list[tuple[str, str]]:
    """Renvoie [(id, event)] des blocs SSE du corps."""
    out: list[tuple[str, str]] = []
    eid = ev = ""
    for line in text.splitlines():
        if line.startswith("id:"):
            eid = line[3:].strip()
        elif line.startswith("event:"):
            ev = line[6:].strip()
        elif line == "" and eid:
            out.append((eid, ev))
            eid = ev = ""
    return out


def test_stream_replays_full_history(tmp_path: Path) -> None:
    client = _client(tmp_path)
    job_id = _launch_and_finish(client)
    resp = client.get(f"/api/runs/{job_id}/events")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")
    events = _parse_sse(resp.text)
    ids = [eid for eid, _ in events]
    states = [ev for _, ev in events]
    # pending → running (un évènement par document, progression) → done.
    # Les ids sont une séquence 1-based contiguë ; bornes pending/done.
    assert ids == [str(i) for i in range(1, len(ids) + 1)]
    assert states[0] == "pending"
    assert states[-1] == "done"
    assert all(s == "running" for s in states[1:-1])


def test_stream_resumes_from_last_event_id(tmp_path: Path) -> None:
    client = _client(tmp_path)
    job_id = _launch_and_finish(client)
    resp = client.get(
        f"/api/runs/{job_id}/events", headers={"Last-Event-ID": "1"}
    )
    ids = [eid for eid, _ in _parse_sse(resp.text)]
    assert ids and ids[0] == "2"  # 1 (pending) déjà vu, repris à partir de 2
    assert "1" not in ids


def test_stream_invalid_last_event_id_replays_all(tmp_path: Path) -> None:
    client = _client(tmp_path)
    job_id = _launch_and_finish(client)
    resp = client.get(
        f"/api/runs/{job_id}/events", headers={"Last-Event-ID": "pas-un-entier"}
    )
    ids = [eid for eid, _ in _parse_sse(resp.text)]
    assert ids == [str(i) for i in range(1, len(ids) + 1)]  # rejeu intégral dès 1


def test_events_unknown_job_is_404(tmp_path: Path) -> None:
    assert _client(tmp_path).get("/api/runs/absent/events").status_code == 404
