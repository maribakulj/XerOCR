"""Lanceur web (TU2.a) : CSRF d'abord, puis launch→exécute→résultat, mode public."""

from __future__ import annotations

import io
import time
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from xerocr.app.engines import engine_statuses
from xerocr.interfaces.web.app import create_app
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


def test_public_mode_allows_local_demo(tmp_path: Path) -> None:
    # la démo n'utilise que `precomputed` (local) → autorisée même en mode public.
    client = _client(tmp_path, public_mode=True)
    resp = client.post("/api/runs", headers=_CSRF)
    assert resp.status_code == 201
    assert _poll_until_terminal(client, resp.json()["job_id"])["state"] == "done"


# --- TU2.d : sélection de moteur + corpus, gardes HTTP -----------------------

_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32


def _post(client: TestClient, body: dict) -> object:
    return client.post("/api/runs", headers=_CSRF, json=body)


def _upload_demo_corpus(client: TestClient) -> str:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("a.png", _PNG)
        zf.writestr("a.gt.txt", b"verite")
    files = {"file": ("c.zip", buf.getvalue(), "application/zip")}
    return client.post("/api/corpus", files=files, headers=_CSRF).json()["corpus_id"]


def test_unknown_engine_is_422(tmp_path: Path) -> None:
    assert _post(_client(tmp_path), {"engine": "bogus"}).status_code == 422


def test_extra_field_is_422(tmp_path: Path) -> None:
    # corps strict (extra interdit) → rejet net.
    resp = _post(_client(tmp_path), {"engine": "precomputed", "x": 1})
    assert resp.status_code == 422


def test_cloud_engine_in_public_mode_is_403(tmp_path: Path) -> None:
    # LE chemin sécurité : un moteur cloud, exposé publiquement, refusé en HTTP.
    resp = _post(_client(tmp_path, public_mode=True), {"engine": "openai"})
    assert resp.status_code == 403


def test_llm_engine_standalone_is_422(tmp_path: Path) -> None:
    # post-correction LLM seule (sans chaîne OCR→LLM) → non exposée.
    assert _post(_client(tmp_path), {"engine": "ollama"}).status_code == 422


def test_unavailable_engine_is_409(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # On FORCE l'indisponibilité du binaire (déterministe : indépendant du fait
    # que tesseract soit installé ou non sur la machine de test/CI).
    monkeypatch.setattr(
        "xerocr.interfaces.web.app.engine_statuses",
        lambda **kw: engine_statuses(has_binary=lambda _name: None, **kw),
    )
    resp = _post(_client(tmp_path), {"engine": "tesseract", "corpus_id": "x"})
    assert resp.status_code in (404, 409)  # 404 si corpus d'abord ; sinon 409
    # sans corpus_id, c'est franchement l'indisponibilité qui parle :
    assert _post(_client(tmp_path), {"engine": "tesseract"}).status_code == 409


def test_unknown_corpus_is_404(tmp_path: Path) -> None:
    resp = _post(_client(tmp_path), {"engine": "precomputed", "corpus_id": "nope"})
    assert resp.status_code == 404


def test_precomputed_with_corpus_is_422(tmp_path: Path) -> None:
    client = _client(tmp_path)
    corpus_id = _upload_demo_corpus(client)
    resp = _post(client, {"engine": "precomputed", "corpus_id": corpus_id})
    assert resp.status_code == 422
