"""Lanceur web (TU2.a) : CSRF d'abord, puis launch→exécute→résultat, mode public."""

from __future__ import annotations

import time
from pathlib import Path

from fastapi.testclient import TestClient

from xerocr.interfaces.web.app import create_app
from xerocr.interfaces.web.routers.runs import blocked_cloud_kinds
from xerocr.interfaces.web.security.csrf import CSRF_HEADER

_CSRF = {CSRF_HEADER: "1"}


def _client(tmp_path: Path, *, public_mode: bool = False) -> TestClient:
    return TestClient(
        create_app(reports_dir=tmp_path, rate_limit=1000, public_mode=public_mode)
    )


def _poll_until_terminal(
    client: TestClient, job_id: str, timeout: float = 30.0
) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        body = client.get(f"/api/runs/{job_id}").json()
        if body["state"] in {"done", "failed", "cancelled"}:
            return body
        time.sleep(0.02)
    raise AssertionError(f"job {job_id} non terminé dans le délai")


# --- Sécurité d'abord (CSRF) -------------------------------------------------


def test_post_without_csrf_is_403(tmp_path: Path) -> None:
    resp = _client(tmp_path).post("/api/runs")
    assert resp.status_code == 403
    # rien n'a été lancé
    assert _client(tmp_path).get("/api/reports").json() == {"reports": []}


def test_cancel_without_csrf_is_403(tmp_path: Path) -> None:
    assert _client(tmp_path).post("/api/runs/whatever/cancel").status_code == 403


def test_csrf_header_allows_post(tmp_path: Path) -> None:
    resp = _client(tmp_path).post("/api/runs", headers=_CSRF)
    assert resp.status_code == 201
    assert "job_id" in resp.json()


# --- Bout-en-bout : lancer → exécuter → résultat visible ---------------------


def test_launch_runs_and_result_appears(tmp_path: Path) -> None:
    client = _client(tmp_path)
    job_id = client.post("/api/runs", headers=_CSRF).json()["job_id"]
    job = _poll_until_terminal(client, job_id)
    assert job["state"] == "done"
    name = job["report_name"]
    # le RunResult produit est listé et rendu par la vitrine read-only
    assert name in client.get("/api/reports").json()["reports"]
    assert client.get(f"/reports/{name}").status_code == 200


def test_status_unknown_job_is_404(tmp_path: Path) -> None:
    assert _client(tmp_path).get("/api/runs/absent").status_code == 404


def test_cancel_unknown_job_is_404(tmp_path: Path) -> None:
    resp = _client(tmp_path).post("/api/runs/absent/cancel", headers=_CSRF)
    assert resp.status_code == 404


# --- Mode public : la gate ---------------------------------------------------


def test_blocked_cloud_kinds_intersects_cloud_only() -> None:
    assert blocked_cloud_kinds(["precomputed", "tesseract", "ollama"]) == frozenset()
    assert blocked_cloud_kinds(["openai", "precomputed"]) == frozenset({"openai"})


def test_public_mode_allows_local_demo(tmp_path: Path) -> None:
    # la démo n'utilise que `precomputed` (local) → autorisée même en mode public.
    client = _client(tmp_path, public_mode=True)
    resp = client.post("/api/runs", headers=_CSRF)
    assert resp.status_code == 201
    assert _poll_until_terminal(client, resp.json()["job_id"])["state"] == "done"
